from dataclasses import dataclass
from typing import TYPE_CHECKING

from injector import inject, singleton
from llama_index.core.chat_engine import ContextChatEngine, SimpleChatEngine
from llama_index.core.chat_engine.types import (
    BaseChatEngine,
)
from llama_index.core.indices import VectorStoreIndex
from llama_index.core.indices.postprocessor import MetadataReplacementPostProcessor
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.postprocessor import (
    SentenceTransformerRerank,
    SimilarityPostprocessor,
)
from llama_index.core.storage import StorageContext
from llama_index.core.types import TokenGen
from pydantic import BaseModel, ConfigDict

from internal_assistant.components.embedding.embedding_component import (
    EmbeddingComponent,
)
from internal_assistant.components.llm.llm_component import LLMComponent
from internal_assistant.components.node_store.node_store_component import (
    NodeStoreComponent,
)
from internal_assistant.components.vector_store.vector_store_component import (
    VectorStoreComponent,
)
from internal_assistant.open_ai.extensions.context_filter import ContextFilter
from internal_assistant.server.chunks.chunks_service import Chunk
from internal_assistant.settings.settings import Settings

if TYPE_CHECKING:
    from llama_index.core.postprocessor.types import BaseNodePostprocessor


class Completion(BaseModel):
    response: str
    sources: list[Chunk] | None = None
    model_config = ConfigDict(arbitrary_types_allowed=True)


class CompletionGen(BaseModel):
    response: TokenGen
    sources: list[Chunk] | None = None
    model_config = ConfigDict(arbitrary_types_allowed=True)


@dataclass
class ChatEngineInput:
    system_message: ChatMessage | None = None
    last_message: ChatMessage | None = None
    chat_history: list[ChatMessage] | None = None

    @classmethod
    def from_messages(cls, messages: list[ChatMessage]) -> "ChatEngineInput":
        # Detect if there is a system message, extract the last message and chat history
        system_message = (
            messages[0]
            if len(messages) > 0 and messages[0].role == MessageRole.SYSTEM
            else None
        )
        last_message = (
            messages[-1]
            if len(messages) > 0 and messages[-1].role == MessageRole.USER
            else None
        )
        # Remove from messages list the system message and last message,
        # if they exist. The rest is the chat history.
        if system_message:
            messages.pop(0)
        if last_message:
            messages.pop(-1)
        chat_history = messages if len(messages) > 0 else None

        return cls(
            system_message=system_message,
            last_message=last_message,
            chat_history=chat_history,
        )


@singleton
class ChatService:
    settings: Settings

    @inject
    def __init__(
        self,
        settings: Settings,
        llm_component: LLMComponent,
        vector_store_component: VectorStoreComponent,
        embedding_component: EmbeddingComponent,
        node_store_component: NodeStoreComponent,
    ) -> None:
        self.settings = settings
        self.llm_component = llm_component
        self.embedding_component = embedding_component
        self.vector_store_component = vector_store_component
        self.storage_context = StorageContext.from_defaults(
            vector_store=vector_store_component.vector_store,
            docstore=node_store_component.doc_store,
            index_store=node_store_component.index_store,
        )
        self.index = VectorStoreIndex.from_vector_store(
            vector_store_component.vector_store,
            storage_context=self.storage_context,
            llm=llm_component.llm,
            embed_model=embedding_component.embedding_model,
            show_progress=True,
        )

    def get_system_inventory(self) -> dict:
        """Get current system document inventory for system awareness"""
        try:
            # Get all documents from storage
            all_docs = list(self.storage_context.docstore.docs.values())

            file_counts = {}
            unique_files = set()
            total_docs = len(all_docs)

            for doc in all_docs:
                if hasattr(doc, "metadata") and doc.metadata:
                    file_name = doc.metadata.get("file_name", "Unknown")
                    unique_files.add(file_name)
                    file_counts[file_name] = file_counts.get(file_name, 0) + 1

            return {
                "total_documents": total_docs,
                "unique_files": len(unique_files),
                "files_list": sorted(list(unique_files)),
                "documents_per_file": file_counts,
            }
        except Exception as e:
            return {
                "total_documents": 0,
                "unique_files": 0,
                "files_list": [],
                "documents_per_file": {},
                "error": str(e),
            }

    def enhance_system_prompt_with_inventory(self, original_prompt: str) -> str:
        """Add system inventory information to the system prompt with enhanced document correlation"""
        inventory = self.get_system_inventory()

        if inventory["total_documents"] == 0:
            inventory_text = "\n\nSYSTEM STATUS: You currently have no documents in your knowledge base."
        else:
            files_summary = ", ".join(inventory["files_list"][:5])
            if len(inventory["files_list"]) > 5:
                files_summary += f" and {len(inventory['files_list']) - 5} more files"

            inventory_text = f"""

CYBERSECURITY INTELLIGENCE SYSTEM:
- You have access to {inventory['unique_files']} unique Files with 📄 {inventory['total_documents']} searchable Segments
- Available files: {files_summary}
- When asked about your knowledge base, reference these specific numbers and available files
- You can search through all these documents to answer questions
- You excel at finding correlations and connections between different documents
- You can identify patterns, inconsistencies, and relationships across your document collection
- Always prioritize information from your document collection over general knowledge when available"""

        return original_prompt + inventory_text

    def _chat_engine(
        self,
        system_prompt: str | None = None,
        use_context: bool = False,
        context_filter: ContextFilter | None = None,
    ) -> BaseChatEngine:
        settings = self.settings

        # DISABLED: Enhance system prompt with enhanced cybersecurity intelligence
        # if system_prompt and use_context:
        #     system_prompt = self.enhance_system_prompt_with_inventory(system_prompt)

        if use_context:
            vector_index_retriever = self.vector_store_component.get_retriever(
                index=self.index,
                context_filter=context_filter,
                similarity_top_k=self.settings.rag.similarity_top_k,
            )
            node_postprocessors: list[BaseNodePostprocessor] = [
                MetadataReplacementPostProcessor(target_metadata_key="window"),
            ]
            if settings.rag.similarity_value:
                node_postprocessors.append(
                    SimilarityPostprocessor(
                        similarity_cutoff=settings.rag.similarity_value
                    )
                )

            if settings.rag.rerank.enabled:
                rerank_postprocessor = SentenceTransformerRerank(
                    model=settings.rag.rerank.model, top_n=settings.rag.rerank.top_n
                )
                node_postprocessors.append(rerank_postprocessor)

            return ContextChatEngine.from_defaults(
                system_prompt=system_prompt,
                retriever=vector_index_retriever,
                llm=self.llm_component.llm,  # Takes no effect at the moment
                node_postprocessors=node_postprocessors,
            )
        else:
            return SimpleChatEngine.from_defaults(
                system_prompt=system_prompt,
                llm=self.llm_component.llm,
            )

    def stream_chat(
        self,
        messages: list[ChatMessage],
        use_context: bool = False,
        context_filter: ContextFilter | None = None,
    ) -> CompletionGen:
        chat_engine_input = ChatEngineInput.from_messages(messages)
        last_message = (
            chat_engine_input.last_message.content
            if chat_engine_input.last_message
            else None
        )

        # Validate message to prevent None/empty vectors from breaking vector search
        if not last_message or (
            isinstance(last_message, str) and last_message.strip() == ""
        ):
            # Return a minimal completion gen for empty messages
            completion_gen = CompletionGen(
                response=iter(["Please provide a valid message."]), sources=[]
            )
            return completion_gen
        system_prompt = (
            chat_engine_input.system_message.content
            if chat_engine_input.system_message
            else None
        )
        chat_history = (
            chat_engine_input.chat_history if chat_engine_input.chat_history else None
        )

        chat_engine = self._chat_engine(
            system_prompt=system_prompt,
            use_context=use_context,
            context_filter=context_filter,
        )
        streaming_response = chat_engine.stream_chat(
            message=last_message.strip() if last_message else "Hello",
            chat_history=chat_history,
        )

        # Collect sources from documents with enhanced correlation
        sources = [Chunk.from_node(node) for node in streaming_response.source_nodes]
        completion_gen = CompletionGen(
            response=streaming_response.response_gen, sources=sources
        )
        return completion_gen

    def chat(
        self,
        messages: list[ChatMessage],
        use_context: bool = False,
        context_filter: ContextFilter | None = None,
    ) -> Completion:
        chat_engine_input = ChatEngineInput.from_messages(messages)
        last_message = (
            chat_engine_input.last_message.content
            if chat_engine_input.last_message
            else None
        )
        system_prompt = (
            chat_engine_input.system_message.content
            if chat_engine_input.system_message
            else None
        )
        chat_history = (
            chat_engine_input.chat_history if chat_engine_input.chat_history else None
        )

        chat_engine = self._chat_engine(
            system_prompt=system_prompt,
            use_context=use_context,
            context_filter=context_filter,
        )
        wrapped_response = chat_engine.chat(
            message=last_message if last_message is not None else "",
            chat_history=chat_history,
        )

        # Collect sources from documents with enhanced correlation
        sources = [Chunk.from_node(node) for node in wrapped_response.source_nodes]
        completion = Completion(response=wrapped_response.response, sources=sources)
        return completion
