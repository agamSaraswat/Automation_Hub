#!/usr/bin/env python3
"""
Applications Dashboard

View:
  - Application status (pending, responded, interviews, offers)
  - Response analytics (response rate, time to response)
  - ROI metrics (cost per application, cost per response, etc.)
  - Individual application details with response tracking

Usage:
  python -m src.jobs.applications_dashboard --status
  python -m src.jobs.applications_dashboard --pending
  python -m src.jobs.applications_dashboard --interviews
  python -m src.jobs.applications_dashboard --roi
"""

import argparse
import json
import logging
from datetime import datetime

from src.jobs.application_tracker import (
    apply_to_job,
    get_applications_by_status,
    get_applications_summary,
    get_roi_analysis,
    record_response,
)

logger = logging.getLogger(__name__)


def cmd_status():
    """Display application status summary."""
    summary = get_applications_summary()
    
    print("\n📊 APPLICATION STATUS SUMMARY\n")
    print(f"  Total Applications: {summary['total_applications']}")
    print(f"  Response Rate: {summary['response_rate']}%")
    print(f"  Avg Time to Response: {summary['avg_time_to_response_days']} days")
    print(f"  Success Rate (Interviews+Offers): {summary['success_rate']}%")
    
    print("\n  By Response Type:")
    for resp_type, count in summary.get("by_response_type", {}).items():
        print(f"    • {resp_type}: {count}")
    
    print()


def cmd_pending():
    """Show pending applications (waiting for response)."""
    pending = get_applications_by_status("pending", limit=20)
    
    print(f"\n⏳ PENDING APPLICATIONS ({len(pending)})\n")
    
    if not pending:
        print("  (no pending applications)\n")
        return
    
    for app in pending:
        days_ago = (datetime.now() - datetime.fromisoformat(app["applied_at"])).days
        print(f"  • {app['title']} @ {app['company']}")
        print(f"    Applied: {days_ago} days ago")
        print(f"    Via: {app['applied_via']}")
        print()


def cmd_interviews():
    """Show applications with scheduled/completed interviews."""
    interviews = get_applications_by_status("interview", limit=20)
    
    print(f"\n🎤 INTERVIEWS ({len(interviews)})\n")
    
    if not interviews:
        print("  (no interviews yet)\n")
        return
    
    for app in interviews:
        print(f"  • {app['title']} @ {app['company']}")
        if app["interview_date"]:
            print(f"    Interview Date: {app['interview_date']}")
        if app["response_text"]:
            print(f"    Message: {app['response_text'][:100]}...")
        print()


def cmd_offers():
    """Show applications with offers."""
    offers = get_applications_by_status("offer", limit=20)
    
    print(f"\n🎉 OFFERS ({len(offers)})\n")
    
    if not offers:
        print("  (no offers yet)\n")
        return
    
    for app in offers:
        print(f"  • {app['title']} @ {app['company']}")
        if app["offer_amount"]:
            print(f"    Offer: {app['offer_amount']}")
        if app["response_text"]:
            print(f"    Details: {app['response_text'][:100]}...")
        print()


def cmd_roi():
    """Display ROI analysis."""
    roi = get_roi_analysis()
    
    print("\n💰 ROI ANALYSIS\n")
    print(f"  Total Cost (estimate): ${roi['total_cost_usd']:.2f}")
    print(f"  Total Applications: {roi['total_applications']}")
    print(f"  Applications/Dollar: {roi['applications_per_dollar']}")
    print(f"  Responses/Dollar: {roi['responses_per_dollar']}")
    print(f"  Cost/Response: ${roi['cost_per_response_usd']:.2f}")
    print(f"  Cost/Interview: ${roi['cost_per_interview_usd']:.2f}")
    print(f"  Est. Cost/Offer: ${roi['estimated_cost_to_offer_usd']:.2f}")
    print()


def cmd_log_response():
    """Log a response to an application (interactive)."""
    print("\n📨 LOG RESPONSE\n")
    
    job_id = input("  Job ID: ").strip()
    if not job_id.isdigit():
        print("  Invalid job ID")
        return
    
    print("\n  Response Type:")
    print("    1. Rejection")
    print("    2. Interview scheduled")
    print("    3. Offer received")
    print("    4. No response yet (cleanup)")
    choice = input("  Choice (1-4): ").strip()
    
    response_map = {"1": "rejected", "2": "interview", "3": "offer", "4": "no_response"}
    response_type = response_map.get(choice)
    
    if not response_type:
        print("  Invalid choice")
        return
    
    print("\n  Response Source: email, phone, platform, linkedin?")
    source = input("  Source: ").strip() or "email"
    
    text = input("  Message (optional): ").strip()
    
    if record_response(int(job_id), response_type, source, text):
        print(f"  ✅ Logged {response_type} for job {job_id}")
    else:
        print(f"  ❌ Error logging response")
    
    print()


def main():
    """Main CLI."""
    parser = argparse.ArgumentParser(
        description="Applications Dashboard",
        epilog="""
Examples:
  python -m src.jobs.applications_dashboard --status
  python -m src.jobs.applications_dashboard --pending
  python -m src.jobs.applications_dashboard --interviews
  python -m src.jobs.applications_dashboard --roi
  python -m src.jobs.applications_dashboard --log-response
        """,
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--status", action="store_true", help="Show status summary")
    group.add_argument("--pending", action="store_true", help="Show pending applications")
    group.add_argument("--interviews", action="store_true", help="Show interviews")
    group.add_argument("--offers", action="store_true", help="Show offers")
    group.add_argument("--roi", action="store_true", help="Show ROI analysis")
    group.add_argument("--log-response", action="store_true", help="Log a response")
    
    args = parser.parse_args()
    
    if args.status:
        cmd_status()
    elif args.pending:
        cmd_pending()
    elif args.interviews:
        cmd_interviews()
    elif args.offers:
        cmd_offers()
    elif args.roi:
        cmd_roi()
    elif args.log_response:
        cmd_log_response()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
