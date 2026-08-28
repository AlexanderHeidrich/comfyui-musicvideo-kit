# Thin wrapper over ./mvkit, for people who type make.
#   make all SONG=federphibien
#   make transcribe SONG=federphibien ENGINE=docker
SONG    ?= federphibien
UNIFORM ?= 10
AUDIO   ?=
ENGINE  ?=
MVKIT   := ./mvkit $(if $(ENGINE),--$(ENGINE),)
export UNIFORM

.PHONY: help doctor drehbuch transcribe scenes refs split draft draft-llm build verify all \
        new concat check docker-build docker-shell docker-clean llm-up llm-down

help:
	@sed -n '2,3p' Makefile
	@echo ""
	@$(MVKIT) help

doctor: ; @$(MVKIT) doctor

drehbuch:   ; $(MVKIT) drehbuch $(SONG)
transcribe: ; $(MVKIT) transcribe $(SONG)
refs:       ; $(MVKIT) refs $(SONG)
draft:      ; $(MVKIT) draft $(SONG)
draft-llm:  ; $(MVKIT) draft $(SONG) --llm
scenes:      ; $(MVKIT) scenes $(SONG)
split:      ; $(MVKIT) split $(SONG)
build:      ; $(MVKIT) build $(SONG)
verify:     ; $(MVKIT) verify $(SONG)
all:        ; $(MVKIT) all $(SONG)

new:
	@test -n "$(AUDIO)" || { echo "usage: make new SONG=<name> AUDIO=<file>"; exit 1; }
	$(MVKIT) new $(SONG) $(AUDIO)

concat:
	@test -n "$(DIR)" || { echo "usage: make concat DIR=<dir-with-mp4s>"; exit 1; }
	$(MVKIT) concat $(DIR)

check:
	@for f in mvkit bin/*.sh; do bash -n $$f && echo "ok  $$f"; done
	@python3 -m py_compile bin/*.py && echo "ok  bin/*.py"
	@rm -rf bin/__pycache__

llm-up:   ; $(MVKIT) llm-up
llm-down: ; $(MVKIT) llm-down

docker-build: ; docker compose build
docker-shell: ; docker compose run --rm mvkit bash
docker-clean: ; docker compose down --rmi local -v
