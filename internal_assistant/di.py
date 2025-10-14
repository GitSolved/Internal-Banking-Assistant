from injector import Injector, singleton

from internal_assistant.settings.settings import Settings, unsafe_typed_settings


def create_application_injector() -> Injector:
    _injector = Injector(auto_bind=True)
    _injector.binder.bind(Settings, to=unsafe_typed_settings)

    # Bind RSS feed service as singleton to maintain cache across requests
    from internal_assistant.server.feeds.feeds_service import RSSFeedService

    _injector.binder.bind(RSSFeedService, to=RSSFeedService(), scope=singleton)

    return _injector


"""
Global injector for the application.

Avoid using this reference, it will make your code harder to test.

Instead, use the `request.state.injector` reference, which is bound to every request
"""
global_injector: Injector = create_application_injector()
