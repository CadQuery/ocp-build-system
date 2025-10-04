.PHONY: cache-clean cache-list cache-size

cache-clean:
	@echo "Call: gh cache delete -a"

cache-list:
	@gh cache list -L 100 | sort -k 2

cache-info: cache-list
	@echo "\nTotal:"
	@gh cache list -L 100 | \
	awk '/MiB/ && $$3 ~ /^[0-9.]+$$/ {sum+=$$3} END {print sum+0}'