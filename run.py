"""
AlphaFactory OS - Run Script
Convenience script that sets up Python path and runs modules
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment
from dotenv import load_dotenv
load_dotenv(project_root / '.env')

# Now you can import and run modules
if __name__ == '__main__':
    # Test database manager
    from src.database.db_manager import db_manager
    from loguru import logger
    
    logger.info("Testing database manager...")
    
    # Initialize database
    db_manager.initialize()
    
    # Test session
    with db_manager.get_session() as session:
        logger.info(f"Session created: {session}")
        logger.success("✓ Database session working!")
    
    # Close connections
    db_manager.close()
    
    logger.success("✓ Database manager test complete!")