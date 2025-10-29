CONDA_ENV := /ssd4/envs/llm_py310_torch271_cu128
ACTIVATE := source $$(conda info --base)/etc/profile.d/conda.sh && conda activate $(CONDA_ENV)

.PHONY: quality
quality:
	@echo "Running quality checks using $(CONDA_ENV)"
	@$(ACTIVATE) && bash scripts/run_quality.sh

.PHONY: test-download
test-download:
	@$(ACTIVATE) && pytest \
		tests/cli/test_playlist_download.py \
		tests/integration/test_cli_download.py \
		tests/cli/test_console_summary.py

.PHONY: test-resume
test-resume:
	@$(ACTIVATE) && pytest \
		tests/persistence/test_resume_progress.py \
		tests/cli/test_resume_command.py

.PHONY: test-metadata
test-metadata:
	@$(ACTIVATE) && pytest \
		tests/db/test_video_recording.py \
		tests/unit/test_subtitles.py \
		tests/perf/test_metadata_latency.py \
		tests/reporting/test_subtitle_coverage.py

.PHONY: test-throttle
test-throttle:
	@$(ACTIVATE) && pytest \
		tests/rate_limit/test_throttle_controls.py \
		tests/unit/test_throttle_cli.py \
		tests/rate_limit/test_throttle_metrics.py
