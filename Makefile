.PHONY: help run-server run-client run-client-gui run-client-terminal clean-runtime

host ?= 127.0.0.1
port ?= 12000
mode ?= gui
server_args ?=
client_args ?=

CLIENT_ARGS = --host $(host) --port $(port)

ifeq ($(mode),terminal)
CLIENT_ARGS += --terminal
endif

help:
	@echo "Targets:"
	@echo "  make run-server [host=ip] [port=n] [server_args='--host ip --port n']"
	@echo "  make run-client [host=ip] [port=n] [mode=gui|terminal] [client_args='--host ip --port n --terminal']"
	@echo "  make run-client-gui [host=ip] [port=n]"
	@echo "  make run-client-terminal [host=ip] [port=n]"
	@echo "  make clean-runtime       # Remove runtime artifacts"

run-server:
	python3 -m server.src.app.server $(if $(strip $(server_args)),$(server_args),--host $(host) --port $(port))

run-client:
	python3 -m client.src.app.client $(if $(strip $(client_args)),$(client_args),$(CLIENT_ARGS))

run-client-gui:
	$(MAKE) run-client mode=gui host=$(host) port=$(port)

run-client-terminal:
	$(MAKE) run-client mode=terminal host=$(host) port=$(port)

clean-runtime:
	python3 -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in [pathlib.Path('client/runtime'), pathlib.Path('server/runtime')]]"
