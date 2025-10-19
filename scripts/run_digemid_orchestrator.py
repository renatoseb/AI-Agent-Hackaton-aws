import sys, os, logging
from datetime import datetime

# Ensure project root on path
sys.path.insert(0, os.getcwd())

from src.dataset.orchestrator import main as orchestrator_main  # type: ignore

# We'll simulate CLI args programmatically

def run():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    since = '2025-09-01'
    until = datetime.utcnow().strftime('%Y-%m-%d')
    output = 'data_output'
    sys.argv = [sys.argv[0], '--plugin', 'pe_digemid_alerts', '--since', since, '--until', until, '--output', output, '--log-level', 'INFO']
    orchestrator_main()
    print('\nOrchestrator run completed. Check raw/ & curated/ for pe_digemid_alerts.')

if __name__ == '__main__':
    run()
