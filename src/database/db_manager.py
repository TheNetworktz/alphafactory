"""
AlphaFactory OS - Database Manager
Handles database connections, session management, and initialization
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from loguru import logger
from typing import Generator

from src.config.config_loader import config
from src.database.models import Base


class DatabaseManager:
    """
    Manages database connections and sessions
    """
    
    def __init__(self):
        """Initialize database manager"""
        self.engine = None
        self.SessionLocal = None
        self._initialized = False
    
    def initialize(self) -> None:
        """
        Initialize database connection and create tables
        """
        if self._initialized:
            logger.info("Database already initialized")
            return
        
        try:
            # Create engine
            database_url = config.database_url
            logger.info(f"Connecting to database...")
            
            self.engine = create_engine(
                database_url,
                pool_pre_ping=True,  # Verify connections before using
                pool_size=10,  # Connection pool size
                max_overflow=20,  # Max overflow connections
                echo=False  # Set to True for SQL query logging
            )
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            # Create all tables
            logger.info("Creating database tables...")
            Base.metadata.create_all(bind=self.engine)
            
            self._initialized = True
            logger.success("✓ Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions
        
        Usage:
            with db_manager.get_session() as session:
                # Do database operations
                session.add(obj)
                session.commit()
        """
        if not self._initialized:
            self.initialize()
        
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def close(self) -> None:
        """Close database connections"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()


if __name__ == '__main__':
    """Test database manager"""
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