# 🔗 Integration Guide: Job Search Hub in Soumyabrata's Ecosystem
## How to Use This Module in Your Larger Automation Projects

**Author:** For Soumyabrata's ecosystem development  
**Purpose:** Clear patterns for integrating job search automation into multi-project environments  
**Updated:** April 9, 2026

---

## 🎯 Integration Philosophy

This codebase is **modular by design**. It works as:
1. **Standalone tool** - Run it yourself for your job search
2. **API module** - Import and use specific functions
3. **Agent toolkit** - Leverage the harness pattern in your agents
4. **Ecosystem component** - Orchestrate with other automation projects

This guide covers integration patterns **2-4**.

---

## 📦 Module Structure for Import

### Available Imports (What You Can Use)

```python
# Core agent pattern (foundation for all your agents)
from src.agent.claude_client import ClaudeClient
from src.agent.tools import define_tools, execute_tool

# Job discovery pipeline
from src.jobs.claude_job_discovery import discover_jobs
from src.jobs.claude_resume_tailoring import tailor_resume
from src.jobs.harness import Harness

# Application tracking and analytics
from src.jobs.application_tracker import ApplicationTracker
from src.jobs.applications_dashboard import ApplicationsDashboard
from src.jobs.deduplicator import JobDeduplicator

# Messaging integrations
from src.messaging.gmail_triage_v2 import EmailTriager
from src.messaging.telegram_bot import TelegramNotifier

# Content generation
from src.linkedin.generator import LinkedInContentGenerator
from src.linkedin.reviewer import ContentReviewer

# Configuration and user management
from src.config.profile_manager import ProfileManager
from src.config.settings_manager import SettingsManager

# Services and utilities
from src.services.token_instrumentation import TokenTracker
from src.services.run_history import RunHistory
from src.services.automation import AutomationOrchestrator

# Scheduling
from src.scheduler.cron import CronScheduler
```

### What NOT to Import (Maintain Compatibility)

These are internal implementation details. Don't import directly:
```python
# ❌ Don't do this
from src.jobs.filtering import internal_filter_logic
from src.jobs.scraper import parse_html_table

# ✅ Do this instead
from src.jobs.claude_job_discovery import discover_jobs
# It handles filtering internally
```

---

## 🚀 Integration Patterns

### Pattern 1: Simple Function Calls (Easiest)

**Use When:** You need a single specific capability without orchestration

```python
# Your ecosystem project: recommendation_engine/main.py

from agam_automation_hub.jobs.claude_job_discovery import discover_jobs
from agam_automation_hub.jobs.application_tracker import ApplicationTracker

def recommend_jobs(user_profile):
    """
    Use job discovery as a component in your recommendation engine.
    """
    # Call the function
    discovered = discover_jobs(
        keywords=user_profile['keywords'],
        experience_level=user_profile['level'],
        limit=20
    )
    
    # Process results
    tracker = ApplicationTracker()
    for job in discovered:
        tracker.add_pending_application(job)
    
    return discovered

# In your Flask/FastAPI app
@app.get("/recommendations")
def get_recommendations(user_id):
    profile = get_user_profile(user_id)
    jobs = recommend_jobs(profile)
    return {"recommended_jobs": jobs}
```

**Pros:** Simple, minimal dependency management, easy to understand  
**Cons:** No shared state, loses context between calls  
**Best for:** One-off integrations, microservices

---

### Pattern 2: Agent Class Wrapper (Flexible)

**Use When:** You want to maintain state and add your own logic

```python
# Your ecosystem: multi_agent_orchestrator/jobs_agent.py

from agam_automation_hub.jobs.harness import Harness
from agam_automation_hub.jobs.claude_job_discovery import discover_jobs
from agam_automation_hub.services.token_instrumentation import TokenTracker

class JobSearchAgentWrapper:
    """
    Wrapper around the job search module for your multi-agent system.
    """
    
    def __init__(self, agent_name="job_searcher"):
        self.name = agent_name
        self.harness = Harness(role="job_discovery_evaluator")
        self.tracker = TokenTracker(agent_name)
        self.memory = {}  # Your agent's memory
    
    def search_and_evaluate(self, query: dict) -> dict:
        """
        Your custom logic built on top of the hub module.
        """
        # Track token usage
        self.tracker.start_operation("job_search")
        
        try:
            # Use the job discovery from the hub
            jobs = discover_jobs(
                keywords=query['keywords'],
                limit=query.get('limit', 10)
            )
            
            # Add your own evaluation logic
            enriched_jobs = []
            for job in jobs:
                # Your custom evaluation
                custom_score = self._my_custom_evaluation(job)
                
                job['custom_score'] = custom_score
                enriched_jobs.append(job)
            
            # Store in memory for context in next call
            self.memory['last_search'] = {
                'query': query,
                'results': enriched_jobs,
                'timestamp': time.time()
            }
            
            # Track completion
            self.tracker.log_operation(
                tokens_used=1000,
                input_tokens=500,
                output_tokens=500
            )
            
            return {
                'success': True,
                'jobs': enriched_jobs,
                'count': len(enriched_jobs),
                'cost': self.tracker.get_cost()
            }
        
        except Exception as e:
            self.tracker.log_error(str(e))
            raise
    
    def _my_custom_evaluation(self, job):
        """Your own business logic on top of the hub."""
        # Implementation
        pass

# Usage in your ecosystem
orchestrator = JobSearchAgentWrapper("job_agent_v1")

result = orchestrator.search_and_evaluate({
    'keywords': ['machine learning', 'python'],
    'limit': 15
})

print(f"Found {result['count']} jobs, cost: ${result['cost']}")
```

**Pros:** Maintains state, integrates your logic, clean interfaces  
**Cons:** More setup, requires careful design  
**Best for:** Multi-agent systems, complex workflows

---

### Pattern 3: Harness Pattern Extension (Powerful)

**Use When:** You want to use the adversarial evaluation pattern for custom tasks

```python
# Your ecosystem: evaluation_system/custom_evaluator.py

from agam_automation_hub.jobs.harness import Harness

class MyCustomEvaluator:
    """
    Implement your own evaluation using the proven harness pattern.
    """
    
    def __init__(self, task_name):
        # Use the adversarial pattern: Planner → Generator → Evaluator
        self.harness = Harness(role=task_name)
    
    def evaluate(self, data):
        """
        Three-stage evaluation:
        1. Plan: What should we evaluate?
        2. Generate: Generate evaluation criteria
        3. Evaluate: Score against criteria
        """
        
        # Stage 1: Planning (done by harness)
        plan = self.harness.plan(data)
        
        # Stage 2: Generation (your custom logic)
        evaluation = self.harness.generate(plan)
        
        # Stage 3: Evaluation (validate and score)
        final_score = self.harness.evaluate(evaluation, data)
        
        return {
            'data': data,
            'plan': plan,
            'evaluation': evaluation,
            'score': final_score['score'],
            'confidence': final_score['confidence'],
            'rationale': final_score['reasoning']
        }

# Use it for ANY evaluation task in your ecosystem
class ContentQualityEvaluator(MyCustomEvaluator):
    def __init__(self):
        super().__init__("content_quality")
    
    def evaluate_article(self, article):
        return self.evaluate({
            'type': 'article',
            'content': article['text'],
            'metadata': article['metadata']
        })

class EmailQualityEvaluator(MyCustomEvaluator):
    def __init__(self):
        super().__init__("email_quality")
    
    def evaluate_email(self, email):
        return self.evaluate({
            'type': 'email',
            'subject': email['subject'],
            'body': email['body'],
            'recipient': email['to']
        })

# Usage
content_eval = ContentQualityEvaluator()
score = content_eval.evaluate_article(article)

email_eval = EmailQualityEvaluator()
score = email_eval.evaluate_email(email)
```

**Pros:** Proven pattern, reduces hallucination, explainable decisions  
**Cons:** Requires understanding the harness pattern  
**Best for:** Building your own agents, quality assurance, evaluation systems

---

### Pattern 4: Service Layer Integration (Enterprise)

**Use When:** You have a full microservices ecosystem

```python
# Your ecosystem: services/job_service/main.py

from fastapi import FastAPI, BackgroundTasks
from agam_automation_hub.services.automation import AutomationOrchestrator
from agam_automation_hub.services.token_instrumentation import TokenTracker
from agam_automation_hub.config import ProfileManager

app = FastAPI()

# Shared instances across your ecosystem
orchestrator = AutomationOrchestrator()
token_tracker = TokenTracker("job_service")
profile_manager = ProfileManager()

@app.post("/discover")
async def async_job_discovery(
    profile_id: str,
    background_tasks: BackgroundTasks
):
    """
    Async job discovery that integrates with your ecosystem.
    """
    # Get user profile
    profile = profile_manager.get_profile(profile_id)
    
    # Enqueue job discovery
    task_id = orchestrator.enqueue_task(
        "job_discovery",
        profile=profile,
        priority="high"
    )
    
    # Track in background
    background_tasks.add_task(
        token_tracker.track_task,
        task_id=task_id
    )
    
    return {"task_id": task_id, "status": "queued"}

@app.get("/status/{task_id}")
async def get_status(task_id: str):
    """Check status of a background task."""
    status = orchestrator.get_task_status(task_id)
    cost = token_tracker.get_cost(task_id)
    
    return {
        "task_id": task_id,
        "status": status['status'],
        "progress": status['progress'],
        "cost_so_far": cost
    }

@app.get("/costs")
async def get_ecosystem_costs():
    """Track costs across all ecosystem services."""
    costs = token_tracker.get_all_costs()
    
    return {
        "total_cost": costs['total'],
        "by_service": costs['breakdown'],
        "by_model": costs['by_model']
    }

# Your orchestrator might invoke multiple ecosystem services
async def full_workflow(user_id: str):
    """
    Orchestrate: Job Discovery → Resume Tailor → Email Notify → Log
    """
    
    profile = profile_manager.get_profile(user_id)
    
    # Step 1: Discover jobs (this module)
    jobs = await orchestrator.run("job_discovery", profile)
    
    # Step 2: Tailor resumes (this module)
    tailored = await orchestrator.run("resume_tailoring", {
        'jobs': jobs,
        'resume': profile['resume']
    })
    
    # Step 3: Send notifications (your ecosystem)
    await orchestrator.run("notification_service", {
        'user_id': user_id,
        'jobs': jobs,
        'tailored': tailored
    })
    
    # Step 4: Log to analytics (your ecosystem)
    await orchestrator.run("analytics_service", {
        'event': 'job_discovery_complete',
        'user_id': user_id,
        'job_count': len(jobs)
    })
    
    return {"success": True, "jobs": len(jobs)}
```

**Pros:** Scalable, tracks costs across ecosystem, async support  
**Cons:** Complex setup, requires understanding services architecture  
**Best for:** Large-scale automation, multiple interconnected services

---

## 🔄 Data Flow Integration

### Standard Data Structures (Work With These)

**Job Object:**
```python
{
    "job_id": "unique-identifier",
    "title": "Senior Software Engineer",
    "company": "TechCorp",
    "location": "Remote",
    "url": "https://...",
    "description": "Full job posting",
    "salary_range": {"min": 120000, "max": 180000},
    "relevance_score": 85,
    "evaluation_rationale": "Matches keywords and experience level",
    "discovered_at": "2026-04-09T10:30:00Z",
    "source": "linkedin|techcrunch|..."
}
```

**Application Tracking Object:**
```python
{
    "application_id": "app-123",
    "job_id": "job-456",
    "user_id": "agam",
    "status": "pending|responded|interview|offer",
    "applied_at": "2026-04-09T11:00:00Z",
    "responded_at": "2026-04-10T09:00:00Z",  # Optional
    "response_type": "rejection|positive|interview|offer",
    "notes": "Follow-up scheduled",
    "tailored_resume_url": "s3://...",
    "cost_tokens": 1250,
    "cost_usd": 0.42
}
```

**Profile Object:**
```python
{
    "user_id": "agam",
    "name": "Agam Saraswat",
    "keywords": ["machine learning", "data science"],
    "target_roles": ["Senior DS", "Lead ML Engineer"],
    "experience_level": "4 years",
    "location_preference": "Remote",
    "master_resume": "/path/to/master_resume.md",
    "settings": {
        "daily_discovery_enabled": True,
        "email_triage_enabled": True,
        "linkedin_posting_enabled": True
    }
}
```

**Always validate against these structures** before passing to functions:
```python
def integrate_job_discovery(jobs_list):
    """Validate jobs before processing in your ecosystem."""
    required_fields = ['job_id', 'title', 'company', 'relevance_score']
    
    for job in jobs_list:
        if not all(field in job for field in required_fields):
            raise ValueError(f"Job missing required fields: {job}")
    
    # Now it's safe to use
    return process_jobs(jobs_list)
```

---

## 🔌 Ecosystem Integration Points

### 1. Configuration Sharing

```python
# Your ecosystem reads the same config
from agam_automation_hub.config import ProfileManager, SettingsManager

class EcosystemConfig:
    """Share configuration across your ecosystem."""
    
    def __init__(self):
        self.profiles = ProfileManager()
        self.settings = SettingsManager()
    
    def get_user_config(self, user_id):
        """Get unified config for a user."""
        profile = self.profiles.get_profile(user_id)
        settings = self.settings.get_settings(user_id)
        
        return {
            'profile': profile,
            'settings': settings,
            'enabled_services': self._get_enabled_services(settings)
        }
    
    def _get_enabled_services(self, settings):
        """Map settings to which ecosystem services to run."""
        return {
            'job_discovery': settings.get('daily_discovery_enabled'),
            'email_triage': settings.get('email_triage_enabled'),
            'linkedin_publishing': settings.get('linkedin_posting_enabled'),
            'your_service': settings.get('your_custom_setting')
        }
```

### 2. Unified Cost Tracking

```python
# All your services use the same token tracker
from agam_automation_hub.services.token_instrumentation import TokenTracker

class EcosystemCostTracker:
    """Track costs across all services."""
    
    def __init__(self):
        self.trackers = {
            'job_search': TokenTracker('job_search'),
            'email_triage': TokenTracker('email_triage'),
            'content_gen': TokenTracker('content_gen'),
            'your_service': TokenTracker('your_service')
        }
    
    def get_total_cost(self, time_period="day"):
        """Get costs for all services."""
        total = 0
        breakdown = {}
        
        for service_name, tracker in self.trackers.items():
            cost = tracker.get_cost_for_period(time_period)
            breakdown[service_name] = cost
            total += cost
        
        return {
            'total': total,
            'breakdown': breakdown,
            'timestamp': datetime.now()
        }
    
    def alert_on_budget(self, max_daily=10.0):
        """Alert if ecosystem spending exceeds budget."""
        total = self.get_total_cost("day")['total']
        
        if total > max_daily:
            # Send alert to your notification system
            self.notify(f"Ecosystem costs exceed ${max_daily}: ${total:.2f}")
```

### 3. Unified Logging & History

```python
# Use the same run history for all services
from agam_automation_hub.services.run_history import RunHistory

class EcosystemRunHistory:
    """Track all ecosystem operations."""
    
    def __init__(self):
        self.history = RunHistory()
    
    def log_job_discovery(self, result):
        """Log job discovery runs."""
        self.history.log_run({
            'service': 'job_discovery',
            'status': result['status'],
            'jobs_found': len(result['jobs']),
            'cost': result['cost']
        })
    
    def log_email_triage(self, result):
        """Log email triage runs."""
        self.history.log_run({
            'service': 'email_triage',
            'emails_processed': result['count'],
            'urgent_count': result['urgent']
        })
    
    def get_ecosystem_health(self):
        """Get overall ecosystem health."""
        return self.history.get_stats({
            'services': ['job_discovery', 'email_triage', ...],
            'period': 'last_7_days'
        })
```

### 4. Multi-Service Orchestration

```python
# Orchestrate across the hub and your other services
from agam_automation_hub.services.automation import AutomationOrchestrator

class EcosystemOrchestrator(AutomationOrchestrator):
    """Extend orchestrator for your ecosystem."""
    
    def run_daily_automation(self, user_id):
        """Run all daily tasks for a user."""
        
        # Step 1: Job discovery (this module)
        job_result = self.run_service('job_discovery', {
            'user_id': user_id
        })
        
        # Step 2: Email triage (this module)
        email_result = self.run_service('email_triage', {
            'user_id': user_id
        })
        
        # Step 3: Your custom service
        your_result = self.run_service('your_service', {
            'user_id': user_id,
            'jobs': job_result['jobs'],
            'emails': email_result['processed']
        })
        
        # Return unified result
        return {
            'jobs_discovered': len(job_result['jobs']),
            'emails_triaged': email_result['count'],
            'your_service_result': your_result,
            'total_cost': sum([
                job_result.get('cost', 0),
                email_result.get('cost', 0),
                your_result.get('cost', 0)
            ])
        }
```

---

## 🧪 Testing Your Integration

### Unit Tests for Your Integration Layer

```python
# tests/test_ecosystem_integration.py

import pytest
from agam_automation_hub.jobs.claude_job_discovery import discover_jobs
from agam_automation_hub.services.token_instrumentation import TokenTracker
from your_ecosystem.job_agent import JobSearchAgentWrapper

class TestJobIntegration:
    """Test that your ecosystem integrates with the job module."""
    
    @pytest.fixture
    def agent(self):
        return JobSearchAgentWrapper()
    
    def test_agent_uses_discovery(self, agent):
        """Verify agent calls discover_jobs correctly."""
        result = agent.search_and_evaluate({
            'keywords': ['python', 'ml'],
            'limit': 5
        })
        
        assert result['success']
        assert len(result['jobs']) > 0
        assert 'custom_score' in result['jobs'][0]
    
    def test_token_tracking(self, agent):
        """Verify token tracking works."""
        result = agent.search_and_evaluate({
            'keywords': ['python'],
            'limit': 5
        })
        
        assert 'cost' in result
        assert result['cost'] > 0  # Actual API call
    
    def test_error_handling(self, agent):
        """Verify error handling in integration."""
        with pytest.raises(Exception):
            agent.search_and_evaluate({
                'keywords': [],  # Invalid: empty keywords
                'limit': 5
            })
    
    def test_state_persistence(self, agent):
        """Verify agent maintains state between calls."""
        agent.search_and_evaluate({
            'keywords': ['python'],
            'limit': 5
        })
        
        # Second call should have memory of first
        assert 'last_search' in agent.memory
        assert agent.memory['last_search']['query']['keywords'] == ['python']
```

### Integration Tests

```python
# tests/test_ecosystem_workflow.py

@pytest.mark.integration
class TestEcosystemWorkflow:
    """Test full ecosystem workflows."""
    
    def test_daily_automation_workflow(self):
        """Test job discovery → tailor → notify workflow."""
        orchestrator = EcosystemOrchestrator()
        
        result = orchestrator.run_daily_automation(
            user_id="test_user"
        )
        
        assert result['jobs_discovered'] > 0
        assert result['emails_triaged'] >= 0
        assert result['total_cost'] >= 0
        assert 'your_service_result' in result
    
    def test_cost_tracking_across_services(self):
        """Verify costs are tracked correctly."""
        tracker = EcosystemCostTracker()
        
        # Run several services
        # ... run job discovery
        # ... run email triage
        # ... run your service
        
        costs = tracker.get_total_cost()
        
        assert costs['total'] > 0
        assert 'job_search' in costs['breakdown']
        assert 'email_triage' in costs['breakdown']
```

---

## 📊 Monitoring Your Integration

### Key Metrics to Track

```python
class IntegrationMetrics:
    """Track integration health."""
    
    def __init__(self):
        self.history = RunHistory()
    
    def get_integration_health(self):
        """Monitor integration status."""
        return {
            # Performance metrics
            'job_discovery_latency': self._avg_latency('job_discovery'),
            'success_rate': self._success_rate('all_services'),
            'avg_cost_per_run': self._avg_cost(),
            
            # Data quality metrics
            'jobs_with_scores': self._jobs_with_scores_count(),
            'deduplication_rate': self._dedup_effectiveness(),
            
            # Ecosystem metrics
            'services_operational': self._count_healthy_services(),
            'error_rate': self._error_rate(),
            
            # Cost metrics
            'daily_cost': self._daily_cost(),
            'cost_trend': self._cost_trend('last_7_days')
        }
    
    def _avg_latency(self, service):
        """Average latency for a service."""
        pass
    
    def _success_rate(self, service):
        """Success rate for service."""
        pass
    
    # ... implement other metrics
```

### Alerting Setup

```python
class IntegrationAlerting:
    """Set up alerts for your integration."""
    
    def __init__(self, email_service, slack_service):
        self.email = email_service
        self.slack = slack_service
    
    def setup_alerts(self):
        """Configure critical alerts."""
        
        # Alert on high error rate
        self.alert_on_condition(
            name="high_error_rate",
            condition=lambda: self.get_error_rate() > 0.1,
            severity="critical",
            notification=self.notify_critical
        )
        
        # Alert on cost overrun
        self.alert_on_condition(
            name="daily_cost_overrun",
            condition=lambda: self.get_daily_cost() > 50,
            severity="warning",
            notification=self.notify_warning
        )
        
        # Alert on service health
        self.alert_on_condition(
            name="service_unhealthy",
            condition=lambda: self.count_healthy_services() < 3,
            severity="critical",
            notification=self.notify_critical
        )
    
    def notify_critical(self, alert):
        """Send critical alert to Slack + Email."""
        self.slack.send(f"🚨 CRITICAL: {alert['name']}")
        self.email.send(f"Critical Alert: {alert['name']}")
    
    def notify_warning(self, alert):
        """Send warning alert."""
        self.slack.send(f"⚠️ WARNING: {alert['name']}")
```

---

## 🔐 Security & Best Practices

### API Key Management

```python
# ❌ Don't do this
from agam_automation_hub.agent.claude_client import ClaudeClient

client = ClaudeClient(api_key="sk-ant-very-secret-key")

# ✅ Do this instead
import os
from agam_automation_hub.agent.claude_client import ClaudeClient

api_key = os.environ.get('ANTHROPIC_API_KEY')
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY not set")

client = ClaudeClient(api_key=api_key)
```

### Profile Isolation

```python
# Ensure users don't access each other's data
from agam_automation_hub.config import ProfileManager

class SecureProfileManager(ProfileManager):
    """Secure profile access with user context."""
    
    def get_profile(self, user_id, requesting_user_id):
        """Only allow users to access their own profiles."""
        if user_id != requesting_user_id:
            raise PermissionError(f"Cannot access {user_id}'s profile")
        
        return super().get_profile(user_id)
```

### Rate Limiting

```python
# Prevent abuse and cost overruns
from agam_automation_hub.services.token_instrumentation import TokenTracker

class RateLimitedTokenTracker(TokenTracker):
    """Track and enforce rate limits."""
    
    def __init__(self, service_name, max_cost_per_day=50):
        super().__init__(service_name)
        self.max_cost_per_day = max_cost_per_day
    
    def log_operation(self, tokens_used, **kwargs):
        """Log but check rate limits."""
        current_cost = self.get_cost_for_period("day")
        operation_cost = self._estimate_cost(tokens_used)
        
        if current_cost + operation_cost > self.max_cost_per_day:
            raise RateLimitError(
                f"Daily limit (${self.max_cost_per_day}) exceeded"
            )
        
        return super().log_operation(tokens_used, **kwargs)
```

---

## 🚀 Deployment & Monitoring

### Docker Integration

```dockerfile
# Your ecosystem Dockerfile

FROM python:3.10-slim

WORKDIR /app

# Install agam automation hub as dependency
RUN git clone https://github.com/agam/automation-hub.git
RUN cd automation-hub && pip install -e .

# Install your ecosystem code
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run your service
CMD ["python", "-m", "your_ecosystem.main"]
```

### Environment Variables

```bash
# .env for your ecosystem integration

# API Keys
ANTHROPIC_API_KEY=sk-ant-...
GMAIL_API_KEY=...
LINKEDIN_API_KEY=...

# Configuration
JOB_HUB_PATH=/app/agam-automation-hub
JOB_HUB_PROFILE=soumyabrata

# Integration settings
ECOSYSTEM_SERVICES=job_discovery,email_triage,your_service
LOG_LEVEL=INFO
COST_ALERT_THRESHOLD=50.0

# Database/Storage
DATA_STORAGE_PATH=/data
LOG_STORAGE_PATH=/logs
```

---

## 📈 Next Steps

1. **Start Simple:** Use Pattern 1 (simple function calls)
2. **Add State:** Move to Pattern 2 (agent wrapper)
3. **Build Evaluators:** Use Pattern 3 (harness extension)
4. **Scale Up:** Move to Pattern 4 (service layer) when ready
5. **Optimize:** Monitor metrics, adjust based on data

---

## 📞 Getting Help

**For integration questions:**
- Check this guide's examples
- Review the main repo's documentation
- Look at test files for usage patterns
- Reach out to Agam via GitHub issues

**For ecosystem-specific patterns:**
- Document your patterns in your own repo
- Share learnings with Agam
- Contribute improvements back to main repo

---

*This integration guide is part of the collaboration framework. Update it as you discover new patterns and best practices.*

**Last Updated:** April 9, 2026
