# whisper.cpp + ffmpeg + python, so the pipeline runs the same on mac, linux and
# windows. The repo itself is bind-mounted by compose, not copied in.
FROM debian:bookworm-slim AS whisper
ARG WHISPER_CPP_REF=v1.9.3
ARG TARGETARCH
RUN apt-get update && apt-get install -y --no-install-recommends \
      git cmake build-essential ca-certificates && rm -rf /var/lib/apt/lists/*
# GGML_NATIVE=OFF: -mcpu=native under gcc-12 resolves to a baseline without fp16
# on Apple Silicon and ggml's NEON fp16 intrinsics then fail to inline.
RUN set -eux; \
    case "${TARGETARCH:-amd64}" in \
      arm64) ARCH_FLAGS="-DGGML_CPU_ARM_ARCH=armv8.2-a+fp16" ;; \
      *)     ARCH_FLAGS="-DGGML_AVX=ON -DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_F16C=ON" ;; \
    esac; \
    git clone --depth 1 --branch "$WHISPER_CPP_REF" \
      https://github.com/ggml-org/whisper.cpp /src; \
    cmake -S /src -B /src/build -DCMAKE_BUILD_TYPE=Release \
      -DBUILD_SHARED_LIBS=OFF -DGGML_NATIVE=OFF $ARCH_FLAGS; \
    cmake --build /src/build -j"$(nproc)" --target whisper-cli

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg python3 curl ca-certificates libgomp1 \
 && rm -rf /var/lib/apt/lists/*
COPY --from=whisper /src/build/bin/whisper-cli /usr/local/bin/whisper-cli
RUN mkdir -p /models /work && chmod 777 /models
ENV WHISPER_MODEL_DIR=/models MVKIT_ENGINE=native HOME=/tmp
WORKDIR /work
ENTRYPOINT []
CMD ["./mvkit", "doctor"]
