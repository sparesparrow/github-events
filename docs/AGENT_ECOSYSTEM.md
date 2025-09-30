# Sparesparrow Agent Ecosystem

## Přehled

GitHub Events Monitor byl rozšířen o komplexní agentový ekosystém pro orchestraci více repozitářů. Systém kombinuje GitHub events monitoring s Claude Agent SDK pro inteligentní koordinaci napříč sparesparrow ekosystémem.

## 🎯 **Cílové Repozitáře**

Systém je optimalizován pro koordinaci těchto repozitářů:

1. **sparesparrow/mcp-prompts** - Katalog prompt šablon
2. **sparesparrow/mcp-project-orchestrator** - Orchestrace projektových workflow
3. **sparesparrow/mcp-router** - Směrování workflow a koordinace agentů  
4. **sparesparrow/podman-desktop-extension-mcp** - Container management
5. **sparesparrow/ai-servis** - AI služby a management

## 🏗️ **Architektura**

### Komponenty Systému

```
┌─────────────────────────────────────────────────┐
│            Claude Agent SDK                     │
│  ┌─────────────────┐  ┌─────────────────────────┐│
│  │ Multi-Repo      │  │ Repository Specialists  ││
│  │ Orchestrator    │  │ (5 specialized agents)  ││
│  └─────────────────┘  └─────────────────────────┘│
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│        GitHub Events MCP Server                 │
│         (Context Provider)                      │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│        GitHub Events Monitor API               │
│      (Repository Context & Analytics)          │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│              AWS DynamoDB                       │
│        (Shared Context Storage)                 │
└─────────────────────────────────────────────────┘
```

### Agentové Specializace

#### **1. Multi-Repo Orchestrator** (Opus)
- **Role**: Koordinace napříč všemi repozitáři
- **Nástroje**: Všechny GitHub events nástroje + orchestrace
- **Context Management**: Prioritizuje koordinační metadata

#### **2. Prompt Librarian** (Sonnet)
- **Repository**: sparesparrow/mcp-prompts
- **Role**: Management prompt katalogu
- **Nástroje**: get_prompt, apply_template, search_prompts

#### **3. Project Orchestrator** (Opus)
- **Repository**: sparesparrow/mcp-project-orchestrator
- **Role**: Komplexní workflow orchestrace
- **Nástroje**: Multi-repo context, deployment readiness

#### **4. Workflow Router** (Opus)
- **Repository**: sparesparrow/mcp-router
- **Role**: Směrování a koordinace workflow
- **Nástroje**: Agent workflow context, security alerts

#### **5. Container Manager** (Sonnet)
- **Repository**: sparesparrow/podman-desktop-extension-mcp
- **Role**: Container deployment a management
- **Nástroje**: Deployment readiness, Bash, container tools

#### **6. AI Service Manager** (Sonnet)
- **Repository**: sparesparrow/ai-servis
- **Role**: AI služby a performance monitoring
- **Nástroje**: Repository health, commits analysis

## 🔄 **Context Management Strategy**

### Optimalizace pro Multi-Repo Operace

```javascript
const contextManagementConfig = {
  edits: [
    {
      type: "clear_tool_uses_20250919",
      trigger: { type: "input_tokens", value: 40000 },
      keep: { type: "tool_uses", value: 5 },
      clear_at_least: { type: "input_tokens", value: 8000 },
      // Nikdy nemazat kritický kontext
      exclude_tools: [
        'get_repository_context',
        'get_multi_repository_context', 
        'get_deployment_readiness',
        'get_agent_workflow_context'
      ]
    }
  ]
};
```

### Context Prioritization

1. **Kritický Context** (nikdy se nemaže):
   - Repository health scores
   - Deployment readiness status
   - Security alerts a dependencies
   - Agent workflow coordination metadata

2. **Operační Context** (maže se při překročení limitu):
   - Detailní commit analýzy
   - Historické event data
   - Staré deployment logy
   - Podrobné file changes

3. **Optimalizace Cache**:
   - Minimum 8000 tokenů při čištění
   - Zachování posledních 5 tool uses
   - Priorita pro coordination nástroje

## 🛠️ **MCP Tools pro Agenty**

### Repository Context Tools

#### `get_repository_context`
```bash
# Kompletní kontext pro jeden repozitář
{
  "repo_name": "sparesparrow/ai-servis",
  "context_type": "full" | "summary" | "commits" | "security"
}
```

#### `get_multi_repository_context`
```bash
# Context pro více repozitářů s dependencies
{
  "repositories": ["sparesparrow/mcp-prompts", "sparesparrow/ai-servis"],
  "include_dependencies": true
}
```

#### `get_deployment_readiness`
```bash
# Assessment deployment readiness
{
  "repositories": ["sparesparrow/mcp-router", "sparesparrow/ai-servis"]
}
```

#### `get_security_alerts`
```bash
# Security alerts napříč repozitáři
{
  "severity": "all" | "high" | "critical"
}
```

#### `get_agent_workflow_context`
```bash
# Context pro workflow orchestraci
{
  "workflow_type": "deployment" | "development" | "review" | "maintenance"
}
```

## 🚀 **Deployment a Spuštění**

### Rychlé Spuštění
```bash
# Nastavení GitHub token
export GITHUB_TOKEN="your_github_token_here"

# Spuštění celého ekosystému
./start_agent_ecosystem.sh
```

### Manuální Spuštění
```bash
# 1. Spuštění DynamoDB a základních služeb
docker-compose -f docker-compose.agents.yml up -d dynamodb-local github-events-api

# 2. Vytvoření DynamoDB tabulek
python scripts/setup_dynamodb.py create

# 3. Spuštění všech agentů
docker-compose -f docker-compose.agents.yml up -d

# 4. Monitoring
docker-compose -f docker-compose.agents.yml logs -f
```

### Jednotlivé Komponenty
```bash
# GitHub Events MCP Server
python scripts/github_events_mcp_server.py

# Repository Agent (v kontejneru)
export TARGET_REPOSITORY=sparesparrow/ai-servis
export AGENT_TYPE=ai_service_manager
python scripts/repository_agent.py

# Agent Dashboard
python scripts/agent_dashboard.py
```

## 📊 **Monitoring a Dashboards**

### Agent Coordination Dashboard
- **URL**: http://localhost:8081
- **Funkce**: Monitoring všech repository agentů
- **Data**: Real-time health, activity, alerts

### GitHub Events API
- **URL**: http://localhost:8080
- **Funkce**: Repository context a analytics
- **Endpoints**: Všechny monitoring endpoints

### DynamoDB Local
- **URL**: http://localhost:8000
- **Funkce**: Shared context storage
- **Data**: Events, commits, metrics, agent state

## 🔧 **Agent Workflow Patterns**

### Pattern 1: Koordinovaný Deployment
```
1. Multi-Repo Orchestrator analyzuje všechny repozitáře
2. Získá deployment readiness pro každý repozitář
3. Vygeneruje optimální deployment sekvenci
4. Koordinuje s Container Manager pro deployment
5. Monitoruje progress a health
```

### Pattern 2: Security Audit
```
1. Ecosystem Coordinator získá security alerts
2. Prioritizuje na základě risk levels
3. Koordinuje security reviews s Repository Specialists
4. Trackuje remediation progress
5. Validuje fixes napříč ekosystémem
```

### Pattern 3: Development Coordination
```
1. Repository Specialists monitorují commit patterns
2. Identifikují cross-repo changes a impacts
3. Koordinují integration testing
4. Managují feature branch synchronization
5. Optimalizují developer productivity
```

## 🔗 **Integrace s MCP Nástroji**

### MCP Prompts Integration
- **Agent**: Prompt Librarian
- **Funkce**: Template management, catalog operations
- **Context**: Prompt usage patterns, template dependencies

### MCP Project Orchestrator Integration  
- **Agent**: Project Orchestrator
- **Funkce**: Workflow coordination, project scaffolding
- **Context**: Project health, deployment sequences

### MCP Router Integration
- **Agent**: Workflow Router
- **Funkce**: Request routing, agent coordination
- **Context**: Routing patterns, agent performance

### Podman Desktop Extension Integration
- **Agent**: Container Manager
- **Funkce**: Container orchestration, deployment
- **Context**: Container health, deployment metrics

## 📈 **Příklady Použití**

### Claude Agent SDK Integration
```javascript
import { query } from '@anthropic/claude-agent-sdk';
import { sparesparrowEcosystemConfig } from './examples/sparesparrow_agent_config.js';

// Koordinovaný deployment
const deploymentResult = query({
  prompt: "Deploy updates across sparesparrow ecosystem with dependency coordination",
  options: sparesparrowEcosystemConfig
});

// Security audit
const securityResult = query({
  prompt: "Perform security audit across all repositories and generate remediation plan",
  options: sparesparrowEcosystemConfig
});
```

### MCP Tools Usage
```bash
# Získání repository context
get_repository_context repo_name="sparesparrow/ai-servis" context_type="full"

# Multi-repository koordinace
get_multi_repository_context repositories=["sparesparrow/mcp-prompts", "sparesparrow/ai-servis"]

# Deployment readiness
get_deployment_readiness repositories=["sparesparrow/mcp-router", "sparesparrow/ai-servis"]
```

## 🔒 **Security a Best Practices**

### Agent Isolation
- Každý agent běží v izolovaném kontejneru
- Shared context pouze přes DynamoDB
- Omezené tool permissions pro každý agent type

### Context Security
- Sensitive data v encrypted storage
- Agent authentication přes GitHub tokens
- Audit trail pro všechny agent actions

### Resource Management
- Container resource limits
- Context size optimization
- Automatic cleanup starých dat

## 🚀 **Výhody Systému**

### Pro Development Teams
- **Koordinovaná orchestrace** napříč více repozitáři
- **Inteligentní deployment** založený na repository health
- **Automatizované security monitoring** a alerts
- **Context-aware decision making** založené na real-time data

### Pro DevOps Teams
- **Container-based agents** pro scalability
- **Shared context storage** v DynamoDB
- **Centralizované monitoring** a coordination
- **Automated workflow optimization**

### Pro AI/ML Teams
- **Specialized AI service management** agent
- **Performance monitoring** a optimization
- **Model deployment coordination**
- **Integration s broader ecosystem**

## 📋 **Dostupné Endpoints**

### Agent Coordination
- `GET /api/dashboard-data` - Complete ecosystem status
- `GET /api/repository/{owner}/{repo}` - Specific repository detail
- `GET /api/ecosystem/summary` - Ecosystem-wide summary

### Repository Context
- `GET /metrics/repository-health?repo=sparesparrow/ai-servis`
- `GET /commits/recent?repo=sparesparrow/mcp-prompts&hours=24`
- `GET /metrics/security-monitoring?repo=sparesparrow/mcp-router`

### Agent Workflow
- `GET /metrics/release-deployment?repo=sparesparrow/podman-desktop-extension-mcp`
- `GET /monitoring/commits?repos=sparesparrow/mcp-prompts,sparesparrow/ai-servis`

## ✨ **Výsledek**

Sparesparrow Agent Ecosystem poskytuje:

✅ **Inteligentní Multi-Repo Orchestraci** s GitHub events context  
✅ **Specializované Repository Agenty** v containerech  
✅ **Context Management** optimalizované pro Claude Agent SDK  
✅ **Real-time Monitoring** a coordination dashboard  
✅ **Scalable Architecture** s DynamoDB backend  
✅ **MCP Integration** pro seamless tool access  
✅ **Security & Compliance** monitoring napříč ekosystémem  

Systém umožňuje inteligentní koordinaci deployment, development a maintenance aktivit napříč všemi vašimi repozitáři s využitím real-time GitHub events dat jako kontextu pro rozhodování agentů.