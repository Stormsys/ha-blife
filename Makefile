# BLife Packages - Home Assistant Integration
# Update these for your setup:
HA_HOST ?= homeassistant.local
HA_USER ?= root
HA_CONFIG_PATH ?= /config

.PHONY: deploy restart logs watch help

help:
	@echo "BLife Packages - Deployment Commands"
	@echo ""
	@echo "  make deploy     - Deploy integration to Home Assistant"
	@echo "  make restart    - Restart Home Assistant"
	@echo "  make logs       - Tail Home Assistant logs (filtered)"
	@echo "  make watch      - Deploy on file changes (requires fswatch)"
	@echo ""
	@echo "Configuration (set via environment or edit Makefile):"
	@echo "  HA_HOST=$(HA_HOST)"
	@echo "  HA_USER=$(HA_USER)"
	@echo "  HA_CONFIG_PATH=$(HA_CONFIG_PATH)"

deploy:
	@echo "🚀 Deploying to $(HA_USER)@$(HA_HOST)..."
	@ssh $(HA_USER)@$(HA_HOST) "mkdir -p $(HA_CONFIG_PATH)/custom_components"
	@if command -v rsync >/dev/null 2>&1; then \
		echo "📦 Using rsync..."; \
		rsync -avz --delete \
			./custom_components/blife_packages/ \
			$(HA_USER)@$(HA_HOST):$(HA_CONFIG_PATH)/custom_components/blife_packages/; \
	else \
		echo "📦 Using tar+ssh (rsync not found)..."; \
		tar czf - -C ./custom_components blife_packages | \
			ssh $(HA_USER)@$(HA_HOST) "mkdir -p $(HA_CONFIG_PATH)/custom_components && \
			cd $(HA_CONFIG_PATH)/custom_components && \
			rm -rf blife_packages && \
			tar xzf -"; \
	fi
	@echo "✅ Deployed! Restart HA to apply changes."

restart:
	@echo "🔄 Restarting Home Assistant..."
	@ssh $(HA_USER)@$(HA_HOST) "ha core restart"
	@echo "⏳ Restart initiated. Wait ~60 seconds for HA to come back up."

logs:
	@echo "📋 Tailing Home Assistant logs (Ctrl+C to stop)..."
	@ssh $(HA_USER)@$(HA_HOST) "tail -f $(HA_CONFIG_PATH)/home-assistant.log" | grep -E "(blife|ERROR|WARNING)"

watch:
	@echo "👀 Watching for changes... (Ctrl+C to stop)"
	@fswatch -o ./custom_components/blife_packages/ | xargs -n1 -I{} make deploy

