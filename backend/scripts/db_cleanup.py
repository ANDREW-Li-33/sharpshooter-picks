import sys
from pathlib import Path
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('db_cleanup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

backend_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(backend_dir))


from db_config import engine


def remove_duplicate_entries():
    """
    Removes duplicate game entries from the database.
    Keeps only one entry for each player-game combination.
    """
    with Session(engine) as session:
        try:
            # First, identify duplicates
            find_duplicates_query = text("""
                SELECT player_id, game_id, COUNT(*) as count
                FROM player_stats
                GROUP BY player_id, game_id
                HAVING COUNT(*) > 1
            """)
            
            duplicate_result = session.execute(find_duplicates_query)
            duplicates = [{"player_id": row[0], "game_id": row[1], "count": row[2]} for row in duplicate_result]
            
            if not duplicates:
                logger.info("No duplicates found. Database is clean.")
                return
                
            logger.info(f"Found {len(duplicates)} sets of duplicate entries")
            
            # For each set of duplicates, keep the earliest entry and delete the rest
            total_deleted = 0
            for dup in duplicates:
                # Get all duplicate entries for this player-game combination
                find_entries_query = text(f"""
                    SELECT id FROM player_stats
                    WHERE player_id = {dup['player_id']} AND game_id = '{dup['game_id']}'
                    ORDER BY id ASC
                """)
                
                entries_result = session.execute(find_entries_query)
                entry_ids = [row[0] for row in entries_result]
                
                # Keep the first one (with the lowest ID), delete the rest
                if len(entry_ids) > 1:
                    ids_to_delete = entry_ids[1:]
                    delete_query = text(f"""
                        DELETE FROM player_stats
                        WHERE id IN ({','.join(str(id) for id in ids_to_delete)})
                    """)
                    
                    result = session.execute(delete_query)
                    deleted_count = result.rowcount
                    total_deleted += deleted_count
                    
                    logger.info(f"Deleted {deleted_count} duplicates for player {dup['player_id']}, game {dup['game_id']}")
            
            session.commit()
            logger.info(f"Successfully removed {total_deleted} duplicate entries")
            
            # Verify the cleanup was successful
            verify_query = text("""
                SELECT player_id, game_id, COUNT(*) as count
                FROM player_stats
                GROUP BY player_id, game_id
                HAVING COUNT(*) > 1
            """)
            
            verify_result = session.execute(verify_query)
            remaining_duplicates = [row for row in verify_result]
            
            if remaining_duplicates:
                logger.warning(f"There are still {len(remaining_duplicates)} sets of duplicates remaining")
            else:
                logger.info("All duplicates successfully removed")
                
        except Exception as e:
            logger.error(f"Error cleaning up database: {e}")
            session.rollback()
            raise

def verify_game_counts():
    """
    Verifies that no player has more than 82 games in a regular season.
    """
    with Session(engine) as session:
        try:
            query = text("""
                SELECT p.player_id, p.full_name, ps.season, COUNT(*) as game_count
                FROM players p
                JOIN player_stats ps ON p.player_id = ps.player_id
                GROUP BY p.player_id, p.full_name, ps.season
                ORDER BY game_count DESC
            """)
            
            result = session.execute(query)
            player_seasons = [{"player_id": row[0], "name": row[1], "season": row[2], "count": row[3]} 
                             for row in result]
            
            issues = []
            for ps in player_seasons:
                if ps["count"] > 82:
                    issues.append(ps)
            
            if issues:
                logger.warning(f"Found {len(issues)} player-seasons with more than 82 games:")
                for issue in issues[:10]:
                    logger.warning(f"  {issue['name']} (ID: {issue['player_id']}): {issue['count']} games in {issue['season']}")
            else:
                logger.info("All player-seasons have 82 or fewer games")
                
        except Exception as e:
            logger.error(f"Error verifying game counts: {e}")
            raise

if __name__ == "__main__":
    logger.info("Starting database cleanup process")
    
    remove_duplicate_entries()
    verify_game_counts()
    
    logger.info("Database cleanup process completed")