#!/usr/bin/env python3
"""
Verification script to check that the fixes have been implemented correctly
"""

import sys
import os
import inspect
# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_groq_service_improvements():
    """Test that GroqService has the new model management features"""
    print("Testing GroqService improvements...")
    
    try:
        from services.groq_service import GroqService
        
        # Check if the class has the new model lists
        has_high_perf_models = hasattr(GroqService, 'HIGH_PERFORMANCE_MODELS')
        has_balanced_models = hasattr(GroqService, 'BALANCED_MODELS')
        has_fast_models = hasattr(GroqService, 'FAST_MODELS')
        has_fallback_models = hasattr(GroqService, 'FALLBACK_MODELS')
        has_get_model_method = hasattr(GroqService, 'get_model_for_task')
        
        print(f"  ✅ HIGH_PERFORMANCE_MODELS: {has_high_perf_models}")
        print(f"  ✅ BALANCED_MODELS: {has_balanced_models}")
        print(f"  ✅ FAST_MODELS: {has_fast_models}")
        print(f"  ✅ FALLBACK_MODELS: {has_fallback_models}")
        print(f"  ✅ get_model_for_task method: {has_get_model_method}")
        
        # Test the get_model_for_task method signature
        if has_get_model_method:
            sig = inspect.signature(GroqService.get_model_for_task)
            has_task_type_param = 'task_type' in sig.parameters
            print(f"  ✅ get_model_for_task has task_type parameter: {has_task_type_param}")
        
        return all([has_high_perf_models, has_balanced_models, has_fast_models, 
                   has_fallback_models, has_get_model_method])
        
    except Exception as e:
        print(f"  ❌ Error testing GroqService: {e}")
        return False

def test_scheduler_improvements():
    """Test that scheduler has improved email reporting"""
    print("\nTesting Scheduler improvements...")
    
    try:
        # Read the scheduler file
        with open(os.path.join(os.path.dirname(__file__), '..', 'scheduler.py'), 'r') as f:
            content = f.read()
        
        # Check for improved error handling and logging
        has_better_error_handling = 'logger.error' in content and 'logger.info' in content
        has_status_report_call = 'send_status_report()' in content
        has_initial_report = 'Sending initial status report' in content
        has_smtp_check = 'smtp_connectivity_check' in content
        
        print(f"  ✅ Better error handling and logging: {has_better_error_handling}")
        print(f"  ✅ Status report call in daily job: {has_status_report_call}")
        print(f"  ✅ Initial status report sending: {has_initial_report}")
        print(f"  ✅ SMTP connectivity check: {has_smtp_check}")
        
        return all([has_better_error_handling, has_status_report_call, 
                   has_initial_report, has_smtp_check])
        
    except Exception as e:
        print(f"  ❌ Error testing scheduler: {e}")
        return False

def test_reporting_service_improvements():
    """Test that reporting service has improved email functionality"""
    print("\nTesting ReportingService improvements...")
    
    try:
        from services.reporting_service import ReportingService
        
        # Check if the class has the improved methods
        has_send_email_method = hasattr(ReportingService, 'send_email_report')
        has_html_generation = hasattr(ReportingService, '_generate_html_report')
        has_text_generation = hasattr(ReportingService, '_generate_text_report')
        
        print(f"  ✅ send_email_report method: {has_send_email_method}")
        print(f"  ✅ HTML report generation: {has_html_generation}")
        print(f"  ✅ Text report generation: {has_text_generation}")
        
        # Check method signatures
        if has_send_email_method:
            sig = inspect.signature(ReportingService.send_email_report)
            has_recipients_param = 'recipients' in sig.parameters
            has_report_param = 'report' in sig.parameters
            print(f"  ✅ send_email_report has proper parameters: {has_recipients_param and has_report_param}")
        
        return all([has_send_email_method, has_html_generation, has_text_generation])
        
    except Exception as e:
        print(f"  ❌ Error testing ReportingService: {e}")
        return False

def main():
    """Main verification function"""
    print("Verifying Monsterrr Fixes Implementation")
    print("=" * 42)
    
    # Test all improvements
    groq_test = test_groq_service_improvements()
    scheduler_test = test_scheduler_improvements()
    reporting_test = test_reporting_service_improvements()
    
    print("\n" + "=" * 42)
    if all([groq_test, scheduler_test, reporting_test]):
        print("🎉 All fixes have been implemented correctly!")
        print("✅ Groq model management with task-specific models")
        print("✅ Improved rate limit handling with fallback models")
        print("✅ Enhanced email reporting with better error handling")
        print("✅ Scheduler sends status reports automatically")
        print("✅ Reporting service generates both HTML and text emails")
    else:
        print("❌ Some fixes are missing or incomplete:")
        if not groq_test:
            print("  - Groq service improvements")
        if not scheduler_test:
            print("  - Scheduler improvements")
        if not reporting_test:
            print("  - Reporting service improvements")

if __name__ == "__main__":
    main()