from celeryconfig import logger, DB_HOST, DB_PORT, DB_USER, DB_PASS
import psycopg2
from psycopg2 import sql
from contextlib import contextmanager
from psycopg2.extras import Json


@contextmanager
def postgres_connection(db_name: str):
    """Контекстный менеджер PostgreSQL."""
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            dbname=db_name,
            connect_timeout=5
        )
        yield conn
    except Exception as e:
        logger.error(f"PostgreSQL connection error: {str(e)}", exc_info=True)
        raise
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception as e:
                logger.error(f"Error closing PostgreSQL connection: {str(e)}", exc_info=True)


def update_video_path(db_name: str, run_id: str, video_path: str) -> bool:
    """Атомарное обновление пути к видео"""
    try:
        with postgres_connection(db_name) as conn:
            with conn.cursor() as cursor:

                if isinstance(video_path, dict):
                    video_path = Json(video_path)

                update_query = sql.SQL("""
                    UPDATE public.run_cases
                    SET video = %s
                    WHERE run_id = %s
                """)

                cursor.execute(update_query, (video_path, run_id))
                conn.commit()

                if cursor.rowcount == 0:
                    logger.warning(f"No rows updated for run_id: {run_id}")
                    return False

                return True
    except Exception as e:
        logger.error(f"Failed to update video path for {run_id}: {str(e)}", exc_info=True)
        return False
