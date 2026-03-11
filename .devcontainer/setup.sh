#!/bin/sh
# Configure starship prompt for zsh
grep -q starship /root/.zshrc 2>/dev/null || echo 'eval "$(starship init zsh)"' >> /root/.zshrc
