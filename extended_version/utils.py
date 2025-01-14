import os
import signal
import subprocess
import logging

logger = logging.getLogger(__name__)

def kill_process(process_name: str) -> None:
    """
    Завершает все процессы с указанным именем
    
    Args:
        process_name: Имя процесса для завершения
    """
    try:
        # Находим PID процессов
        cmd = f"pgrep -f {process_name}"
        output = subprocess.getoutput(cmd)
        
        if output:
            # Убиваем каждый процесс
            for pid in output.split('\n'):
                try:
                    os.kill(int(pid), signal.SIGTERM)
                    logger.info(f"Process {pid} ({process_name}) terminated")
                except ProcessLookupError:
                    continue
                except Exception as e:
                    logger.error(f"Error killing process {pid}: {str(e)}")
    except Exception as e:
        logger.error(f"Error finding processes: {str(e)}")
