{
  "agents": {
    "defaults": {
      "reasoningDefault": "stream",
      "thinkingDefault": "high",
      "contextPruning": {
        "mode": "cache-ttl",
        "ttl": "90s",
        "softTrimRatio": 0.06,
        "keepLastAssistants": 5,
        "softTrim": {
          "maxChars": 3200,
          "headChars": 1200,
          "tailChars": 1000
        },
        "hardClear": {
          "enabled": false
        }
      },
      "heartbeat": {
        "every": "0m",
        "isolatedSession": true
      },
      "model": {
        "primary": "xiaoyiprovider/Auto-Model"
      },
      "compaction": {
        "mode": "safeguard",
        "reserveTokens": 120000,
        "recentTurnsPreserve": 2,
        "memoryFlush": {
          "enabled": false
        }
      },
      "memorySearch": {
        "enabled": true,
        "sources": [
          "memory",
          "sessions"
        ],
        "provider": "openai",
        "model": "xiaoyiprovider/text-embedding-v1.0",
        "fallback": "none",
        "experimental": {
          "sessionMemory": true
        },
        "multimodal": {
          "enabled": false
        },
        "remote": {
          "baseUrl": "https://celia-claw-drcn.ai.dbankcloud.cn/celia-claw/v1/rest-api",
          "apiKey": "apikey",
          "headers": {
            "x-request-from": "openclaw",
            "x-hag-trace-id": "openclaw-embedding-trace-id",
            "x-uid": "30086000724011528",
            "x-api-key": "__REPLACE_ME_x-api-key__"
          }
        },
        "chunking": {
          "tokens": 128,
          "overlap": 16
        },
        "sync": {
          "watch": true,
          "intervalMinutes": 5,
          "sessions": {
            "deltaBytes": 15000,
            "deltaMessages": 15,
            "postCompactionForce": true
          }
        },
        "store": {
          "fts": {
            "tokenizer": "trigram"
          }
        },
        "query": {
          "maxResults": 10,
          "minScore": 0.1,
          "hybrid": {
            "enabled": true,
            "vectorWeight": 1,
            "textWeight": 0,
            "candidateMultiplier": 4
          }
        },
        "cache": {
          "enabled": true
        }
      },
      "subagents": {
        "allowAgents": [
          "*"
        ],
        "maxConcurrent": 8
      }
    },
    "list": [
      {
        "id": "main",
        "subagents": {
          "allowAgents": [
            "*"
          ]
        }
      },
      {
        "id": "zhuzhu",
        "name": "zhuzhu",
        "workspace": "/home/sandbox/.openclaw/workspace/株株",
        "agentDir": "/home/sandbox/.openclaw/agents/zhuzhu/agent",
        "model": "xiaoyiprovider/Auto-Model",
        "identity": {
          "name": "株株",
          "emoji": "🌲",
          "theme": "森林"
        }
      },
      {
        "id": "music-champion",
        "name": "music-champion",
        "workspace": "/home/sandbox/.openclaw/workspace",
        "agentDir": "/home/sandbox/.openclaw/agents/music-champion/agent",
        "model": "xiaoyiprovider/Auto-Model",
        "identity": {
          "name": "🎵 音乐创作师_M2",
          "emoji": "🎵",
          "theme": "music"
        }
      }
    ]
  },
  "gateway": {
    "mode": "local",
    "auth": {
      "mode": "token",
      "token": "__REPLACE_ME_token__"
    },
    "controlUi": {
      "allowedOrigins": [
        "http://localhost:18789",
        "http://127.0.0.1:18789"
      ]
    }
  },
  "meta": {
    "lastTouchedVersion": "2026.5.6",
    "lastTouchedAt": "2026-06-28T18:05:50.161Z"
  },
  "discovery": {
    "mdns": {
      "mode": "off"
    }
  },
  "messages": {
    "queue": {
      "mode": "steer"
    }
  },
  "session": {
    "dmScope": "per-peer"
  },
  "skills": {
    "limits": {
      "maxSkillsPromptChars": 30000
    },
    "load": {
      "extraDirs": [
        "~/.openclaw/workspace/skills/",
        "/home/sandbox/core_skills/"
      ],
      "watch": true,
      "watchDebounceMs": 250
    },
    "entries": {
      "experimental-memory-install": {
        "enabled": false
      },
      "experimental-memory-status": {
        "enabled": false
      },
      "experimental-memory-uninstall": {
        "enabled": false
      },
      "experimental-memory-upgrade": {
        "enabled": false
      },
      "healthcheck": {
        "enabled": false
      },
      "node-connect": {
        "enabled": false
      },
      "taskflow": {
        "enabled": false
      },
      "taskflow-inbox-triage": {
        "enabled": false
      }
    }
  },
  "models": {
    "mode": "replace",
    "providers": {
      "xiaoyiprovider": {
        "timeoutSeconds": 600,
        "baseUrl": "https://celia-claw-drcn.ai.dbankcloud.cn/celia-claw/v1/sse-api",
        "api": "openai-completions",
        "apiKey": "apiKey",
        "headers": {
          "Accept": "text/event-stream",
          "x-request-from": "openclaw",
          "x-uid": "30086000724011528",
          "x-api-key": "__REPLACE_ME_x-api-key__"
        },
        "models": [
          {
            "id": "Auto-Model",
            "name": "Auto-Model",
            "reasoning": false,
            "input": [
              "text"
            ],
            "cost": {
              "input": 0.001,
              "output": 0.002,
              "cacheRead": 0,
              "cacheWrite": 0
            },
            "contextWindow": 256000,
            "maxTokens": 6000
          }
        ]
      }
    }
  },
  "browser": {
    "enabled": true,
    "remoteCdpTimeoutMs": 5000,
    "remoteCdpHandshakeTimeoutMs": 10000,
    "color": "#FF4500",
    "executablePath": "/home/sandbox/chrome-headless.sh",
    "headless": true,
    "noSandbox": true,
    "attachOnly": false,
    "defaultProfile": "openclaw",
    "ssrfPolicy": {
      "dangerouslyAllowPrivateNetwork": true
    },
    "tabCleanup": {
      "enabled": true,
      "idleMinutes": 3,
      "maxTabsPerSession": 12,
      "sweepMinutes": 5
    },
    "profiles": {
      "openclaw": {
        "cdpPort": 18800,
        "color": "#FF4500"
      },
      "work": {
        "cdpPort": 18801,
        "color": "#0066CC"
      }
    }
  },
  "tools": {
    "deny": [
      "web_search",
      "tts",
      "canvas"
    ],
    "profile": "full",
    "sessions": {
      "visibility": "all"
    }
  },
  "hooks": {
    "internal": {
      "enabled": true,
      "entries": {
        "bootstrap-extra-files": {
          "enabled": true,
          "paths": [
            "/opt/security/AGENTS.md"
          ]
        }
      }
    }
  },
  "channels": {
    "xiaoyi-channel": {
      "wsUrl1": "wss://celia-claw-drcn.ai.dbankcloud.cn/openclaw/v1/xiaoyi/ws/link",
      "wsUrl2": "wss://celia-claw-drcn.ai.dbankcloud.cn/openclaw/v1/xiaoyi/ws/link",
      "apiKey": "__REPLACE_ME_apiKey__",
      "agentId": "agent208b6760552b4fa0b395e5165d0d771e",
      "apiId": "webhook7f59df0b98a64234919",
      "pushId": 123456,
      "uid": "30086000724011528",
      "enabled": true,
      "fileUploadUrl": "https://celia-claw-drcn.ai.dbankcloud.cn",
      "pushUrl": ""
    }
  },
  "plugins": {
    "entries": {
      "execution-validator-plugin": {
        "enabled": true
      },
      "xiaoyi-channel": {
        "enabled": true
      },
      "llm-router": {
        "enabled": true
      },
      "file-transfer": {
        "enabled": false
      },
      "tool-truncator": {
        "enabled": true
      },
      "memory-celia": {
        "enabled": true,
        "hooks": {
          "allowConversationAccess": true
        },
        "config": {
          "serverBinaryPath": "/home/sandbox/.openclaw/extensions/celia_memory/install/current/bin/celia_memory_mcp_server",
          "dbPath": "/home/sandbox/.openclaw/workspace/memory/celia_memory/celia_memory.db",
          "chat": {
            "model": "LLM_DeepSeekV4",
            "headers": {
              "x-request-from": "openclaw",
              "Accept": "text/event-stream"
            }
          }
        }
      },
      "browser": {
        "enabled": true
      },
      "deepseek": {
        "enabled": true
      }
    },
    "load": {
      "paths": [
        "/home/sandbox/core_plugins/execution-validator-plugin",
        "/home/sandbox/.openclaw/extensions/celia_memory/install/current/memory-plugin"
      ]
    },
    "slots": {
      "memory": "memory-celia"
    }
  },
  "mcp": {
    "servers": {
      "知识卡云容器": {
        "url": "http://101.245.88.123:8888/mcp/sse"
      }
    }
  }
}