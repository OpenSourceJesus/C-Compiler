.PHONY: tests clean

# Default optimization level (can be overridden: make tests OPT_LEVEL=O0)
OPT_LEVEL ?= O0

# Default number of benchmark runs (can be overridden: make tests RUNS=10)
RUNS ?=

# Include paths (can be overridden: make tests INCLUDE_PATHS="include lib")
# Multiple paths should be space-separated, e.g., INCLUDE_PATHS="include lib"
INCLUDE_PATHS ?=

tests:
	@echo "=========================================="
	@echo "Running benchmarks for all tests"
	@echo "=========================================="
	@echo "Optimization level: $(OPT_LEVEL)"
	@if [ -n "$(RUNS)" ]; then \
		echo "Number of runs: $(RUNS)"; \
	fi
	@if [ -n "$(INCLUDE_PATHS)" ]; then \
		echo "Include paths: $(INCLUDE_PATHS)"; \
	fi
	@echo ""
	@test_count=0; \
	success_count=0; \
	fail_count=0; \
	opt_level_flag=""; \
	if [ -n "$(OPT_LEVEL)" ]; then \
		opt_level_flag="--opt-level $(OPT_LEVEL)"; \
	fi; \
	runs_flag=""; \
	if [ -n "$(RUNS)" ]; then \
		runs_flag="--runs $(RUNS)"; \
	fi; \
	include_flags=""; \
	if [ -n "$(INCLUDE_PATHS)" ]; then \
		for include_path in $(INCLUDE_PATHS); do \
			include_flags="$$include_flags -I $$include_path"; \
		done; \
	fi; \
	for test_file in Tests/*.c; do \
		if [ -f "$$test_file" ]; then \
			test_count=$$((test_count + 1)); \
			echo "=========================================="; \
			echo "Test $$test_count: $$test_file"; \
			echo "=========================================="; \
			if /usr/bin/python3 benchmark.py "$$test_file" $$opt_level_flag $$runs_flag $$include_flags; then \
				success_count=$$((success_count + 1)); \
				echo ""; \
				echo "✓ Test $$test_count ($$test_file) PASSED"; \
			else \
				fail_count=$$((fail_count + 1)); \
				echo ""; \
				echo "✗ Test $$test_count ($$test_file) FAILED"; \
			fi; \
			echo ""; \
		fi; \
	done; \
	for test_dir in Tests/*/; do \
		if [ -d "$$test_dir" ]; then \
			test_count=$$((test_count + 1)); \
			echo "=========================================="; \
			echo "Test $$test_count: $$test_dir"; \
			echo "=========================================="; \
			if /usr/bin/python3 benchmark.py "$$test_dir" $$opt_level_flag $$runs_flag $$include_flags; then \
				success_count=$$((success_count + 1)); \
				echo ""; \
				echo "✓ Test $$test_count ($$test_dir) PASSED"; \
			else \
				fail_count=$$((fail_count + 1)); \
				echo ""; \
				echo "✗ Test $$test_count ($$test_dir) FAILED"; \
			fi; \
			echo ""; \
		fi; \
	done; \
	echo "=========================================="; \
	echo "Test Summary"; \
	echo "=========================================="; \
	echo "Total tests: $$test_count"; \
	echo "Passed: $$success_count"; \
	echo "Failed: $$fail_count"; \
	echo "=========================================="; \
	if [ $$fail_count -gt 0 ]; then \
		exit 1; \
	fi

clean:
	@echo "Cleaning up build artifacts..."
	@rm -rf gcc_output custom_output
	@rm -f Tests/*.asm Tests/*.o
	@find Tests -name "*.asm" -delete
	@find Tests -name "*.o" -delete
	@find Tests -name "*.exe" -delete
	@echo "Clean complete."
