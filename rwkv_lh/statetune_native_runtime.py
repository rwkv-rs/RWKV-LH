"""Admission of the single frozen Native trainer, its code, ABI and CUDA binary."""
from __future__ import annotations

import importlib.metadata
import os
from pathlib import Path, PurePosixPath
import sys
from typing import Any, Mapping

from rwkv_lh import statetune_core as a

NATIVE_RUNTIME_VERSION = "rwkv-lh.statetune-native-runtime.v2"
NATIVE_BUILD_VERSION = "rwkv-lh.statetune-native-build.v1"
NATIVE_EXECUTION = {"wkv_mode": "fp32io16", "gemm_accumulation": "fp32", "token_dtype": "float16",
                    "state_dtype": "float32", "batch_size": 1, "head_size": 64}
CFLAGS = ["-O3", "-Wno-psabi"]
CUDA_FLAGS = ["-O3", "--expt-relaxed-constexpr", "--expt-extended-lambda", "-lineinfo"]
TRANSLATION_UNITS = ("bindings.cpp", "validation.cpp", "validation/recurrent_metadata.cu",
    "common/wkv7/recurrent_common_fp32io16.cpp", "common/wkv7/recurrent_common_fp32io16_forward.cu",
    "common/wkv7/recurrent_common_fp32io16_backward.cu")


def training_source_files(root: str | Path) -> list[Path]:
    root = Path(root).resolve()
    paths = {p for p in (root / "rwkv_lh").rglob("*")
             if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}
    paths.update((root / "scripts").rglob("*.py"))
    paths.update(root / name for name in ("pyproject.toml", "uv.lock") if (root / name).is_file())
    return sorted(paths)


def native_source_records(root: str | Path) -> list[dict[str, Any]]:
    root = Path(root).resolve()
    return [{"path": str(path.relative_to(root)), "sha256": a.sha256_file(path)}
            for path in sorted((root / "rwkv_lh/statetune_native_csrc").rglob("*")) if path.is_file()]


def _sealed_ref(value: Mapping[str, Any]) -> dict[str, Any]:
    a.require(set(value) == {"path", "sha256"}, "native identity requires an exact sealed reference")
    return a.read_sealed_json(value["path"], value["sha256"])


def verify_project_source(reference: Mapping[str, Any], source_root: Path) -> None:
    manifest = _sealed_ref(reference)
    a.require(manifest.get("schema_version") == "rwkv-lh.uploaded-project-source.v1"
              and Path(manifest["remote_root"]).resolve() == source_root.resolve(),
              "native project source root or manifest version differs")
    expected = {}
    for row in manifest["files"]:
        path = PurePosixPath(row["path"])
        a.require(not path.is_absolute() and '..' not in path.parts and row["path"] not in expected,
                  "native source path is unsafe or duplicated")
        expected[row["path"]] = (row["sha256"], row["bytes"])
    actual = {}
    for path in source_root.rglob('*'):
        a.require(not path.is_symlink(), "native project source contains a symlink")
        if path.is_file() and '__pycache__' not in path.parts:
            actual[path.relative_to(source_root).as_posix()] = (a.sha256_file(path), path.stat().st_size)
    a.require(bool(expected) and actual == expected, "complete native project source inventory differs")


def verify_build(build: Mapping[str, Any], source_root: Path) -> None:
    a.require(build.get("schema_version") == NATIVE_BUILD_VERSION, "native build version differs")
    a.require(build.get("source_files") == native_source_records(source_root), "native compiled source inventory differs")
    a.require(build.get("cflags") == CFLAGS and build.get("cuda_flags") == CUDA_FLAGS,
              "native compiler arithmetic flags differ")
    a.require(build.get("module_name") == "rwkv_lh_r26_decay_fp32", "native binary entry point differs")
    a.require(set(build.get("extension", {})) == {"path", "sha256"}, "native extension identity is missing")
    a.verify_file(build["extension"]["path"], build["extension"]["sha256"])
    a.require(isinstance(build.get("compiler"), dict) and isinstance(build.get("environment"), dict),
              "native compiler and ABI identities are missing")
    compiler = build["compiler"]
    for name in ("nvcc", "cxx", "python"):
        ref = compiler.get(name, {})
        a.require(set(ref) == {"path", "sha256", "version"} and bool(ref["version"]), "native compiler identity is incomplete")
        a.verify_file(ref["path"], ref["sha256"])
    _sealed_ref(compiler["toolchain_manifest"])
    a.verify_file(build["build_ninja"]["path"], build["build_ninja"]["sha256"])


def verify_native_runtime(path: str | Path, sha256: str, *, source_root: str | Path,
                          source_manifest_sha256: str) -> dict[str, Any]:
    source_root = Path(source_root).resolve()
    runtime = a.read_sealed_json(path, sha256)
    a.require(set(runtime) == {"schema_version", "source_manifest", "execution", "engine",
                              "model_artifact", "build", "dependencies"}
              and runtime["schema_version"] == NATIVE_RUNTIME_VERSION, "native runtime fields or version differ")
    a.require(runtime["source_manifest"]["sha256"] == source_manifest_sha256,
              "native runtime was not bound to this complete training source")
    verify_project_source(runtime["source_manifest"], source_root)
    a.require(runtime["execution"] == NATIVE_EXECUTION, "native training execution profile differs")
    engine = runtime["engine"]
    a.require(set(engine) == {"root", "manifest_path", "manifest_sha256", "revision"}, "native engine identity is incomplete")
    from rwkv_lh.state_router.local_backend import _validate_engine_source_manifest
    _validate_engine_source_manifest(Path(engine["manifest_path"]), engine["manifest_sha256"],
        engine_root=Path(engine["root"]), engine_revision=engine["revision"])
    build = _sealed_ref(runtime["build"])
    verify_build(build, source_root)
    dependencies = _sealed_ref(runtime["dependencies"])
    a.require(Path(sys.executable).resolve() == Path(dependencies["python_executable"]).resolve(),
              "native training Python executable differs")
    for package, version in dependencies["packages"].items():
        a.require(importlib.metadata.version(package) == version, "native installed dependency differs: " + package)
    flash_root = Path(dependencies["flash_package_root"]).resolve()
    flash_actual = {str(p.resolve()) for p in flash_root.rglob("*")
                    if p.is_file() and "__pycache__" not in p.parts}
    a.require(flash_actual == {str(Path(row["path"]).resolve()) for row in dependencies["flash_files"]},
              "complete FlashRWKV package inventory differs")
    for section in ("flash_files", "loaded_libraries"):
        a.require(isinstance(dependencies.get(section), list) and bool(dependencies[section]), "native dependency inventory is missing")
        for row in dependencies[section]:
            a.verify_file(row["path"], row["sha256"])
    import torch
    a.require(build["environment"]["torch_version"] == str(torch.__version__)
              and build["environment"]["torch_cuda"] == torch.version.cuda
              and build["environment"]["torch_cxx11_abi"] == torch._C._GLIBCXX_USE_CXX11_ABI,
              "compiled extension Torch/CUDA ABI differs")
    artifact = runtime["model_artifact"]
    a.require(set(artifact) == {"path", "manifest_sha256"}, "native model artifact identity is incomplete")
    manifest = a.read_sealed_json(Path(artifact["path"]) / "manifest.json", artifact["manifest_sha256"])
    a.require(manifest.get("schema_version") == "rwkv-lh.vllm-rwkv-artifact.v1", "native model manifest version differs")
    a.verify_file(Path(artifact["path"]) / "config.json", manifest["output"]["config_sha256"])
    return runtime


def load_native_runtime(runtime: Mapping[str, Any]) -> None:
    import torch
    engine = Path(runtime["engine"]["root"]).resolve()
    os.environ["VLLM_RWKV7_WKV_MODE"] = NATIVE_EXECUTION["wkv_mode"]
    sys.path.insert(0, str(engine))
    import flash_rwkv
    dependencies = _sealed_ref(runtime["dependencies"])
    a.require(Path(flash_rwkv.__file__).resolve().parent == Path(dependencies["flash_package_root"]).resolve(),
              "native trainer imported a different FlashRWKV package")
    import vllm
    import vllm.rwkv7_ops  # noqa: F401
    a.require(Path(vllm.__file__).resolve().is_relative_to(engine), "native trainer imported a different engine")
    build = _sealed_ref(runtime["build"])
    a.require(list(torch.cuda.get_device_capability()) == build["environment"]["gpu_capability"],
              "compiled native extension GPU architecture differs")
    from rwkv_lh.statetune_native_recurrence import load_extension
    load_extension(build["extension"]["path"], build["extension"]["sha256"])
    torch.backends.cuda.matmul.allow_fp16_accumulation = False
    torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction = False
    torch.backends.cuda.matmul.allow_tf32 = False


def verify_loaded_libraries(runtime: Mapping[str, Any]) -> None:
    """Reject actual binary loads absent from the sealed environment or engine."""
    dependencies = _sealed_ref(runtime["dependencies"])
    known = {str(Path(row["path"]).resolve()): row["sha256"] for row in dependencies["loaded_libraries"]}
    engine = runtime["engine"]
    engine_manifest = a.read_sealed_json(engine["manifest_path"], engine["manifest_sha256"])
    known.update({str((Path(engine["root"]) / row["path"]).resolve()): row["sha256"]
                  for row in engine_manifest["files"] if ".so" in row["path"]})
    build = _sealed_ref(runtime["build"])
    known[str(Path(build["extension"]["path"]).resolve())] = build["extension"]["sha256"]
    actual = set()
    for line in Path("/proc/self/maps").read_text().splitlines():
        fields = line.split(maxsplit=5)
        if len(fields) == 6 and fields[5].startswith("/") and ".so" in fields[5]:
            a.require(not fields[5].endswith(" (deleted)"), "a loaded native dependency was deleted")
            actual.add(str(Path(fields[5]).resolve()))
    a.require(actual <= set(known), "unregistered shared libraries were loaded: " + ", ".join(sorted(actual - set(known))))
    for path in sorted(actual):
        a.verify_file(path, known[path])
