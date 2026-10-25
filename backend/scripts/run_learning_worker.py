"""Dedicated worker: python scripts/run_learning_worker.py --watch"""
import argparse
import fcntl
import os
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.core.db import SessionLocal
from app.services.education_worker import run_one

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--watch',action='store_true');parser.add_argument('--limit',type=int,default=1);args=parser.parse_args()
    # Multiple service invocations cannot run the same model queue concurrently.
    lock_dir=Path.home()/'.cache/cortex-education'
    lock_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
    lock=open(lock_dir/'worker.lock','a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:raise SystemExit('An education worker is already active')
    processed=0
    while True:
        job=run_one(SessionLocal)
        if job is not None:
            processed+=1;print(f'Education job {job} finished',flush=True)
        if not args.watch and (job is None or processed>=args.limit):break
        if job is None:time.sleep(10)
