.PHONY: help target local-target gcp-target pr-gate pr-gate-hub contract

help:
	@./bin/sentinel help

target local-target:
	@./bin/sentinel --local target

gcp-target:
	@./bin/sentinel --gcp target

pr-gate:
	@./bin/sentinel --local pr-gate

pr-gate-hub:
	@./bin/sentinel --local pr-gate-hub

contract:
	@./bin/sentinel --local contract
