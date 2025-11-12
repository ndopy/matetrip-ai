#!/bin/bash
set -e

# 로그 출력을 위한 함수
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# S3에서 .env 파일 다운로드 (환경 변수로 S3 경로가 설정된 경우)
if [ -n "$S3_ENV_PATH" ]; then
    log "Downloading .env from S3: $S3_ENV_PATH"
    aws s3 cp "$S3_ENV_PATH" /app/.env
    if [ $? -eq 0 ]; then
        log ".env file downloaded successfully from S3"
    else
        log "WARNING: Failed to download .env from S3, using default values"
    fi
fi

log "Starting matetrip-ai services..."

# FastAPI 서버 시작 (백그라운드)
log "Starting FastAPI server on 0.0.0.0:8000..."
uvicorn main:app --host 0.0.0.0 --port 8000 > >(sed 's/^/[SERVER] /') 2>&1 &
SERVER_PID=$!

# 서버가 준비될 때까지 대기
log "Waiting for server to be ready..."
sleep 5

# 스크립트 시작 (백그라운드)
log "Starting processing script..."
# 배치 크기를 환경 변수로 제어 (기본값: 20)
BATCH_SIZE=${BATCH_SIZE:-5}
log "Batch size: $BATCH_SIZE"
python scripts/process_existing_places_parallel.py --batch-size $BATCH_SIZE > >(sed 's/^/[SCRIPT] /') 2>&1 &
SCRIPT_PID=$!

log "Services started successfully!"
log "  - FastAPI Server PID: $SERVER_PID"
log "  - Processing Script PID: $SCRIPT_PID"
log "Server is running and will continue even after script completes."

# 서버 프로세스가 종료될 때까지 대기 (스크립트가 완료되어도 서버는 계속 실행)
wait $SERVER_PID
EXIT_CODE=$?

log "Server exited with code $EXIT_CODE"
exit $EXIT_CODE
