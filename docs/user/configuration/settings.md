# Settings and Configuration

The configuration of your Internal Assistant server is done thanks to `settings` files (more precisely `settings.yaml`).
These text files are written using the [YAML](https://en.wikipedia.org/wiki/YAML) syntax.

While Internal Assistant is distributing safe and universal configuration files, you might want to quickly customize your
Internal Assistant, and this can be done using the `settings` files.

This project is defining the concept of **profiles** (or configuration profiles).
This mechanism, using your environment variables, is giving you the ability to easily switch between
configuration you've made.

A typical use case of profile is to easily switch between LLM and embeddings.
To be a bit more precise, you can change the language (to French, Spanish, Italian, English, etc) by simply changing
the profile you've selected; no code changes required!

Internal Assistant is configured through *profiles* that are defined using yaml files, and selected through env variables.
The full list of properties configurable can be found in `settings.yaml`.

## How to know which profiles exist

Profiles are stored in multiple locations:
- **Environment profiles**: `config/environments/{profile}.yaml` (e.g., `local.yaml`, `test.yaml`, `docker.yaml`)
- **Model profiles**: `config/model-configs/{profile}.yaml` (e.g., `ollama.yaml`, `openai.yaml`)
- **Legacy profiles**: `config/settings-{profile}.yaml` (for backward compatibility)

To see available profiles:
```bash
ls config/environments/
ls config/model-configs/
```

## How to use an existing profiles
**Please note that the syntax to set the value of an environment variables depends on your OS**.
You have to set environment variable `PGPT_PROFILES` to the name of the profile you want to use.

For example, on **linux and macOS**, this gives:
```bash
export PGPT_PROFILES=my_profile_name_here
```

Windows Command Prompt (cmd) has a different syntax:
```shell
set PGPT_PROFILES=my_profile_name_here
```

Windows Powershell has a different syntax:
```shell
$env:PGPT_PROFILES="my_profile_name_here"
```
If the above is not working, you might want to try other ways to set an env variable in your window's terminal.

---

Once you've set this environment variable to the desired profile, you can simply launch your Internal Assistant,
and it will run using your profile on top of the default configuration.

## Reference
Additional details on the profiles are described in this section

### Environment variable `PGPT_SETTINGS_FOLDER`

The location of the settings folder. Defaults to `config/`.
Should contain the default `settings.yaml` and profile directories.

### Environment variable `PGPT_PROFILES`

By default, the configuration in `config/settings.yaml` is loaded.
Using this env var you can load additional profiles; format is a comma separated list of profile names.

The system searches for profiles in this order:
1. `config/environments/{profile}.yaml`
2. `config/model-configs/{profile}.yaml`
3. `config/settings-{profile}.yaml` (legacy)

Profile contents are merged on top of the base settings, with later profiles overriding earlier ones.

**Examples:**
- `PGPT_PROFILES=local` loads `config/environments/local.yaml`
- `PGPT_PROFILES=test` loads `config/environments/test.yaml`
- `PGPT_PROFILES=local,docker` loads both profiles, with docker settings taking precedence

### Environment variables expansion

Configuration files can contain environment variables,
they will be expanded at runtime.

Expansion must follow the pattern `${VARIABLE_NAME:default_value}`.

For example, the following configuration will use the value of the `PORT`
environment variable or `8001` if it's not set.
Missing variables with no default will produce an error.

```yaml
server:
  port: ${PORT:8001}
```
