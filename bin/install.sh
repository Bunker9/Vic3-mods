#!/usr/bin/env sh
# Registers hkvault git aliases (repo-local) for the Vic3 hk/config vault.
# Run once per machine from anywhere inside the repo:  sh bin/install.sh
set -e
git config alias.seal   '!python bin/hkvault.py seal'
git config alias.unseal '!python bin/hkvault.py unseal'
git config alias.vault  '!python bin/hkvault.py verify'
echo "Installed git aliases:"
echo "  git seal     encrypt changed *.md -> *.md.age, then commit"
echo "  git unseal   decrypt *.md.age -> *.md  (recovery)"
echo "  git vault    verify no plaintext *.md is tracked"
