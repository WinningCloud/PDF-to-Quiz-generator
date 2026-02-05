import os
import json
import hashlib
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import re
import random
import string
from pathlib import Path
import shutil

def generate_unique_id(prefix: str = "") -> str:
    """
    Generate unique ID
    
    Args:
        prefix: Optional prefix for the ID
        
    Returns:
        Unique ID string
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    random_str = uuid.uuid4().hex[:8]
    unique_id = f"{prefix}_{timestamp}_{random_str}" if prefix else f"{timestamp}_{random_str}"
    return unique_id

def safe_json_dumps(data: Any, indent: int = 2) -> str:
    """
    Safely dump data to JSON string
    
    Args:
        data: Data to convert to JSON
        indent: Indentation level
        
    Returns:
        JSON string
    """
    def default_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, set):
            return list(obj)
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)
    
    return json.dumps(data, default=default_serializer, indent=indent, ensure_ascii=False)

def safe_json_loads(json_str: str) -> Any:
    """
    Safely load JSON string
    
    Args:
        json_str: JSON string
        
    Returns:
        Parsed data
    """
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # Try to fix common JSON issues
        json_str = json_str.replace("'", '"')
        json_str = re.sub(r'(\w+):', r'"\1":', json_str)
        return json.loads(json_str)

def calculate_md5(file_path: str) -> str:
    """
    Calculate MD5 hash of file
    
    Args:
        file_path: Path to file
        
    Returns:
        MD5 hash string
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def ensure_directory(directory_path: str) -> str:
    """
    Ensure directory exists
    
    Args:
        directory_path: Path to directory
        
    Returns:
        Created directory path
    """
    os.makedirs(directory_path, exist_ok=True)
    return directory_path

def clean_filename(filename: str) -> str:
    """
    Clean filename by removing special characters
    
    Args:
        filename: Original filename
        
    Returns:
        Cleaned filename
    """
    # Remove invalid characters
    cleaned = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove multiple underscores
    cleaned = re.sub(r'_+', '_', cleaned)
    
    # Remove leading/trailing underscores and dots
    cleaned = cleaned.strip('_.')
    
    # Ensure not empty
    if not cleaned:
        cleaned = "file"
    
    # Limit length
    if len(cleaned) > 255:
        name, ext = os.path.splitext(cleaned)
        name = name[:255 - len(ext)]
        cleaned = name + ext
    
    return cleaned

def get_file_size(file_path: str) -> int:
    """
    Get file size in bytes
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in bytes
    """
    if os.path.exists(file_path):
        return os.path.getsize(file_path)
    return 0

def format_file_size(size_bytes: int) -> str:
    """
    Format file size to human readable string
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

def chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split list into chunks
    
    Args:
        items: List to split
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

def flatten_list(nested_list: List[List[Any]]) -> List[Any]:
    """
    Flatten nested list
    
    Args:
        nested_list: Nested list
        
    Returns:
        Flattened list
    """
    return [item for sublist in nested_list for item in sublist]

def remove_duplicates_preserve_order(items: List[Any]) -> List[Any]:
    """
    Remove duplicates while preserving order
    
    Args:
        items: List with possible duplicates
        
    Returns:
        List without duplicates
    """
    seen = set()
    return [x for x in items if not (x in seen or seen.add(x))]

def get_random_string(length: int = 8) -> str:
    """
    Generate random string
    
    Args:
        length: Length of string
        
    Returns:
        Random string
    """
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for _ in range(length))

def validate_email(email: str) -> bool:
    """
    Validate email format
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_url(url: str) -> bool:
    """
    Validate URL format
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/[-\w._~:/?#[\]@!$&\'()*+,;%=]*)?$'
    return re.match(pattern, url) is not None

def parse_datetime(datetime_str: str) -> Optional[datetime]:
    """
    Parse datetime from string
    
    Args:
        datetime_str: Datetime string
        
    Returns:
        Parsed datetime or None
    """
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(datetime_str, fmt)
        except ValueError:
            continue
    
    return None

def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime to string
    
    Args:
        dt: Datetime object
        format_str: Format string
        
    Returns:
        Formatted datetime string
    """
    return dt.strftime(format_str)

def time_ago(dt: datetime) -> str:
    """
    Get human readable time ago string
    
    Args:
        dt: Datetime object
        
    Returns:
        Time ago string
    """
    now = datetime.utcnow()
    diff = now - dt
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "just now"

def retry_with_backoff(
    func,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple = (Exception,)
):
    """
    Retry function with exponential backoff
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exceptions: Exceptions to catch
        
    Returns:
        Function result
        
    Raises:
        Last exception if all retries fail
    """
    import time
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except exceptions as e:
            if attempt == max_retries:
                raise
            
            # Calculate delay with exponential backoff
            delay = min(max_delay, base_delay * (2 ** attempt))
            
            # Add jitter
            jitter = random.uniform(0, delay * 0.1)
            delay += jitter
            
            time.sleep(delay)
    
    raise RuntimeError("Should not reach here")

def batch_process(
    items: List[Any],
    process_func,
    batch_size: int = 100,
    **kwargs
) -> List[Any]:
    """
    Process items in batches
    
    Args:
        items: Items to process
        process_func: Processing function
        batch_size: Batch size
        **kwargs: Additional arguments for process_func
        
    Returns:
        Processed results
    """
    results = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_results = process_func(batch, **kwargs)
        results.extend(batch_results)
    
    return results

def create_backup(file_path: str, backup_dir: str = "backups") -> Optional[str]:
    """
    Create backup of file
    
    Args:
        file_path: Path to file to backup
        backup_dir: Backup directory
        
    Returns:
        Backup file path or None
    """
    if not os.path.exists(file_path):
        return None
    
    # Create backup directory
    os.makedirs(backup_dir, exist_ok=True)
    
    # Generate backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.basename(file_path)
    backup_name = f"{filename}.backup_{timestamp}"
    backup_path = os.path.join(backup_dir, backup_name)
    
    # Copy file
    shutil.copy2(file_path, backup_path)
    
    return backup_path

def cleanup_old_files(
    directory: str,
    pattern: str = "*",
    max_age_days: int = 30,
    max_files: int = 100
) -> List[str]:
    """
    Cleanup old files in directory
    
    Args:
        directory: Directory to clean
        pattern: File pattern to match
        max_age_days: Maximum age in days
        max_files: Maximum number of files to keep
        
    Returns:
        List of deleted files
    """
    if not os.path.exists(directory):
        return []
    
    # Get all files matching pattern
    import glob
    files = glob.glob(os.path.join(directory, pattern))
    
    # Sort by modification time (oldest first)
    files.sort(key=os.path.getmtime)
    
    deleted = []
    now = time.time()
    max_age_seconds = max_age_days * 24 * 60 * 60
    
    for file_path in files:
        # Check if we should delete based on age
        file_age = now - os.path.getmtime(file_path)
        
        # Check if we should delete based on count
        files_remaining = len(files) - len(deleted)
        
        if file_age > max_age_seconds or files_remaining > max_files:
            try:
                os.remove(file_path)
                deleted.append(file_path)
            except OSError:
                pass
    
    return deleted

def calculate_percentage(part: float, whole: float) -> float:
    """
    Calculate percentage
    
    Args:
        part: Part value
        whole: Whole value
        
    Returns:
        Percentage
    """
    if whole == 0:
        return 0.0
    return (part / whole) * 100

def normalize_score(score: float, min_score: float = 0.0, max_score: float = 1.0) -> float:
    """
    Normalize score to 0-1 range
    
    Args:
        score: Original score
        min_score: Minimum possible score
        max_score: Maximum possible score
        
    Returns:
        Normalized score
    """
    if max_score == min_score:
        return 0.0
    
    normalized = (score - min_score) / (max_score - min_score)
    return max(0.0, min(1.0, normalized))

def weighted_average(values: List[float], weights: List[float]) -> float:
    """
    Calculate weighted average
    
    Args:
        values: List of values
        weights: List of weights
        
    Returns:
        Weighted average
    """
    if not values or not weights or len(values) != len(weights):
        return 0.0
    
    total_weight = sum(weights)
    if total_weight == 0:
        return 0.0
    
    weighted_sum = sum(v * w for v, w in zip(values, weights))
    return weighted_sum / total_weight