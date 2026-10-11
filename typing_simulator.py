import time
from datetime import datetime

async def simulate_typing_session(dataset_sample, policy_callback):
    """Simulates a real-world typing session using AmazonQAC sequences."""
    prefixes = dataset_sample.get("prefixes", [])
    session_id = dataset_sample.get("session_id")
    
    start_time_str = dataset_sample.get("first_prefix_typed_time")
    end_time_str = dataset_sample.get("search_time")
    
    print(f"\n[Session {session_id}]")
    
    # Calculate true average time per prefix state
    time_per_step = 0.5 # fallback
    if start_time_str and end_time_str:
        try:
            start_dt = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S.%f")
            # Handle cases where search_time lacks milliseconds
            if "." in end_time_str:
                end_dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S.%f")
            else:
                end_dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
                
            total_seconds = (end_dt - start_dt).total_seconds()
            
            if len(prefixes) > 1 and total_seconds > 0:
                time_per_step = total_seconds / len(prefixes)
        except ValueError:
            pass # Use fallback if parsing fails

    for i, current_prefix in enumerate(prefixes):
        # Print the entire state to reflect backspacing seen in the raw data
        print(f"\rTyping state: {current_prefix:<40}", end="", flush=True)

        decision_context = {
            "session_id": session_id,
            "current_prefix": current_prefix,
            "step": i
        }
        
        await policy_callback(decision_context)
        
        # Use the strictly derived average time, no invented pauses
        time.sleep(time_per_step)

    print("\n--- Session Complete ---\n")

async def mock_policy(context):
    pass