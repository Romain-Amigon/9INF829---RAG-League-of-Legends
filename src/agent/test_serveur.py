# -*- coding: utf-8 -*-
"""
Created on Wed Jun  3 15:25:00 2026

@author: ramigon
"""

import sys
import os

sys.stderr.write("⚙️ Démarrage du test des imports...\n")
sys.stderr.flush()

sys.stderr.write("1. Import de mcp...\n")
sys.stderr.flush()
from mcp.server.fastmcp import FastMCP
sys.stderr.write("✅ mcp OK.\n")
sys.stderr.flush()

sys.stderr.write("2. Import de llama_index.core...\n")
sys.stderr.flush()
from llama_index.core import StorageContext, load_index_from_storage, Settings
sys.stderr.write("✅ llama_index.core OK.\n")
sys.stderr.flush()

sys.stderr.write("3. Import de llama_index.embeddings...\n")
sys.stderr.flush()
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
sys.stderr.write("✅ huggingface OK.\n")
sys.stderr.flush()

sys.stderr.write("🎉 Tous les imports ont réussi !\n")
sys.exit(0)