"""Local vllm-rwkv feature backend for the State Router."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from rwkv_lh.model_io import canonical_digest


# The Router head is trained in the RWKV-LH process.  This must be set before
# that process imports Torch or performs its first CUDA operation.
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VLLM_RWKV_ROOT = Path("/home/chase/GitHub/vllm-rwkv")
DEFAULT_VLLM_RWKV_REVISION = "67f0c5996c50dca0ad779da545cb491527de988f"
DEFAULT_ROUTER_MODEL = ROOT / "data/models/rwkv7-0.4b-g1-vllm-v1"
DEFAULT_ROUTER_COMPATIBILITY_SHA256 = (
    "ddd321386a9d45ded66f4805a823bf5135d2681c7f1231053361255ad6561f10"
)
DEFAULT_VLLM_RWKV_PYTHON = DEFAULT_VLLM_RWKV_ROOT / ".venv/bin/python"
DEFAULT_RUNTIME_TEMP = ROOT / "temp/vllm-rwkv-runtime"
LOCAL_BACKEND_VERSION = "rwkv-lh.local-vllm-rwkv.v1"
WORKER_REQUEST_SCHEMA = "rwkv-lh.state-router-vllm-worker-request.v1"
WORKER_RESPONSE_SCHEMA = "rwkv-lh.state-router-vllm-worker-response.v1"
MODEL_MANIFEST_SCHEMA = "rwkv-lh.vllm-rwkv-artifact.v1"
MODEL_COMPATIBILITY_SCHEMA = "rwkv-lh.vllm-rwkv-portable-identity.v1"
RUNTIME_DERIVATION_SCHEMA = "rwkv-lh.vllm-rwkv-runtime-derivation.v1"
RUNTIME_SOURCE_VALIDATION_SCHEMA = (
    "rwkv-lh.vllm-rwkv-fp32-cmix-source-validation.v1"
)
_PROFILE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_value(root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _validate_runtime_derivation(
    path: Path,
    expected_sha256: str,
    *,
    model_manifest_path: Path,
    model_artifact_engine_revision: str,
    model_weights_sha256: str,
    runtime_engine_root: Path,
    runtime_engine_revision: str,
    runtime_build_profile_sha256: str,
    runtime_source_path: Path,
) -> dict[str, Any]:
    """Validate an explicit proof for running one artifact on a derived engine."""

    resolved = path.resolve()
    if not resolved.is_file() or _file_sha256(resolved) != expected_sha256:
        raise RuntimeError("local runtime derivation manifest checksum mismatch")
    value = json.loads(resolved.read_text(encoding="utf-8"))
    artifact = value.get("model_artifact") or {}
    runtime = value.get("runtime_engine") or {}
    validation = value.get("validation") or {}
    if not (
        value.get("schema_version") == RUNTIME_DERIVATION_SCHEMA
        and value.get("model_format_unchanged") is True
        and value.get("model_weights_unchanged") is True
        and value.get("tokenizer_unchanged") is True
        and value.get("raw_outputs_modified") is False
        and artifact.get("manifest_sha256") == _file_sha256(model_manifest_path)
        and artifact.get("engine_revision") == model_artifact_engine_revision
        and artifact.get("weights_sha256") == model_weights_sha256
        and runtime.get("revision") == runtime_engine_revision
        and runtime.get("build_profile_sha256")
        == runtime_build_profile_sha256
        and runtime.get("rwkv7_sha256") == _file_sha256(runtime_source_path)
    ):
        raise RuntimeError("local runtime derivation contract changed")
    recorded_engine_root = Path(str(runtime.get("path") or ""))
    if not recorded_engine_root.is_absolute():
        recorded_engine_root = ROOT / recorded_engine_root
    if recorded_engine_root.resolve() != runtime_engine_root.resolve():
        raise RuntimeError("local runtime derivation engine path changed")
    validation_path = Path(str(validation.get("path") or ""))
    if not validation_path.is_absolute():
        validation_path = ROOT / validation_path
    validation_sha256 = str(validation.get("sha256") or "")
    if not (
        _SHA256_PATTERN.fullmatch(validation_sha256)
        and validation_path.is_file()
        and _file_sha256(validation_path) == validation_sha256
    ):
        raise RuntimeError("local runtime derivation validation checksum mismatch")
    evidence = json.loads(validation_path.read_text(encoding="utf-8"))
    evidence_engine = evidence.get("engine") or {}
    cases = evidence.get("cases") or ()
    if not (
        evidence.get("schema_version") == RUNTIME_SOURCE_VALIDATION_SCHEMA
        and evidence.get("status") == "passed"
        and evidence.get("eligible") is True
        and evidence.get("model_weights_sha256") == model_weights_sha256
        and evidence.get("generated_rwkv_text_count") == 0
        and evidence.get("sampling_invocation_count") == 0
        and evidence.get("raw_outputs_modified") is False
        and evidence_engine.get("revision") == runtime_engine_revision
        and evidence_engine.get("build_profile_sha256")
        == runtime_build_profile_sha256
        and evidence_engine.get("rwkv7_sha256")
        == runtime.get("rwkv7_sha256")
        and len(cases) >= 1
        and all(
            case.get("eligible") is True
            and case.get("repeat_bitwise_equal") is True
            and case.get("adapter_bitwise_equal") is True
            for case in cases
        )
    ):
        raise RuntimeError("local runtime derivation validation is not eligible")
    return {
        "manifest": str(resolved),
        "manifest_sha256": expected_sha256,
        "model_artifact_engine_revision": model_artifact_engine_revision,
        "runtime_engine_revision": runtime_engine_revision,
        "validation": str(validation_path.resolve()),
        "validation_sha256": validation_sha256,
    }


def _portable_identity(base: Mapping[str, Any]) -> dict[str, Any]:
    """Return the path-independent numerical feature identity."""

    source = base.get("model_source")
    selected_source = source if isinstance(source, Mapping) else {}
    identity = {
        "schema_version": MODEL_COMPATIBILITY_SCHEMA,
        "backend_version": base["backend_version"],
        "engine_revision": base["engine_revision"],
        "engine_build_profile": base["engine_build_profile"],
        "engine_build_profile_sha256": base["engine_build_profile_sha256"],
        "torch_version": base["engine_torch_version"],
        "transformers_version": base["engine_transformers_version"],
        "model_source": {
            "model": selected_source.get("model"),
            "revision": selected_source.get("revision"),
            "sha256": selected_source.get("sha256"),
        },
        "model_config_sha256": base["model_config_sha256"],
        "model_weights_sha256": base["model_weights_sha256"],
        "hidden_size": base["hidden_size"],
        "num_hidden_layers": base["num_hidden_layers"],
        "head_size": base["head_size"],
        "vocab_size": base["vocab_size"],
        "tokenizer_class": base["tokenizer_class"],
        "tokenizer_vocab_sha256": base["tokenizer_vocab_sha256"],
        "tokenizer_vocab_size": base["tokenizer_vocab_size"],
        "bos_token_id": base["bos_token_id"],
        "eos_token_id": base["eos_token_id"],
        "pad_token_id": base["pad_token_id"],
        "truncation_side": base["truncation_side"],
        "max_tokens": base["max_tokens"],
        "wkv_mode": base["wkv_mode"],
        "dtype": base["dtype"],
    }
    if "state_profile" in base:
        identity["state_profile"] = dict(base["state_profile"])
    return identity


@dataclass(frozen=True)
class LocalVLLMRWKVSettings:
    engine_root: Path = DEFAULT_VLLM_RWKV_ROOT
    engine_revision: str = DEFAULT_VLLM_RWKV_REVISION
    model_artifact_engine_revision: str = ""
    engine_python: Path = DEFAULT_VLLM_RWKV_PYTHON
    model: Path = DEFAULT_ROUTER_MODEL
    batch_size: int = 16
    max_tokens: int = 1024
    wkv_mode: str = "fp16"
    runtime_temp: Path = DEFAULT_RUNTIME_TEMP
    compatibility_sha256: str = DEFAULT_ROUTER_COMPATIBILITY_SHA256
    runtime_derivation_manifest: Path | None = None
    runtime_derivation_manifest_sha256: str = ""
    state_profile_manifest: Path | None = None
    state_profile_manifest_sha256: str = ""
    state_profile_id: str = ""
    state_profile_sha256: str = ""

    def __post_init__(self) -> None:
        for name in ("engine_root", "engine_python", "model", "runtime_temp"):
            object.__setattr__(self, name, Path(getattr(self, name)).expanduser())
        if self.runtime_derivation_manifest is not None:
            object.__setattr__(
                self,
                "runtime_derivation_manifest",
                Path(self.runtime_derivation_manifest).expanduser(),
            )
        if self.state_profile_manifest is not None:
            object.__setattr__(
                self,
                "state_profile_manifest",
                Path(self.state_profile_manifest).expanduser(),
            )
        if not self.engine_revision.strip() or len(self.engine_revision) != 40:
            raise ValueError("local vllm-rwkv revision must be a full Git commit")
        artifact_revision = (
            self.model_artifact_engine_revision or self.engine_revision
        )
        object.__setattr__(
            self, "model_artifact_engine_revision", artifact_revision
        )
        if len(artifact_revision) != 40:
            raise ValueError(
                "local model-artifact engine revision must be a full Git commit"
            )
        derivation_configured = (
            self.runtime_derivation_manifest is not None,
            bool(self.runtime_derivation_manifest_sha256),
        )
        if any(derivation_configured) and not all(derivation_configured):
            raise ValueError(
                "local runtime derivation requires manifest and manifest SHA-256"
            )
        revisions_differ = artifact_revision != self.engine_revision
        if revisions_differ != all(derivation_configured):
            raise ValueError(
                "a derived runtime engine requires one explicit derivation manifest"
            )
        if self.runtime_derivation_manifest_sha256 and not _SHA256_PATTERN.fullmatch(
            self.runtime_derivation_manifest_sha256
        ):
            raise ValueError("local runtime derivation SHA-256 is invalid")
        if self.batch_size < 1 or self.max_tokens < 8:
            raise ValueError("local vllm-rwkv batch_size/max_tokens are too small")
        if self.wkv_mode not in {"fp16", "fp32io16"}:
            raise ValueError("local vllm-rwkv WKV mode must be fp16 or fp32io16")
        if len(self.compatibility_sha256) != 64 or any(
            item not in "0123456789abcdef" for item in self.compatibility_sha256
        ):
            raise ValueError("local Router compatibility SHA-256 must be explicit")
        configured = (
            self.state_profile_manifest is not None,
            bool(self.state_profile_manifest_sha256),
            bool(self.state_profile_id),
            bool(self.state_profile_sha256),
        )
        if any(configured) and not all(configured):
            raise ValueError(
                "local RWKV state profile requires manifest, manifest SHA-256, "
                "profile ID, and profile SHA-256"
            )
        if self.state_profile_id and not _PROFILE_ID_PATTERN.fullmatch(
            self.state_profile_id
        ):
            raise ValueError("local RWKV state-profile ID is invalid")
        for name, value in (
            ("manifest", self.state_profile_manifest_sha256),
            ("profile", self.state_profile_sha256),
        ):
            if value and not _SHA256_PATTERN.fullmatch(value):
                raise ValueError(
                    f"local RWKV state-profile {name} SHA-256 is invalid"
                )


class LocalVLLMRWKVExtractor:
    """Extract hidden, recurrent-state, and logits with local vllm-rwkv."""

    def __init__(self, settings: LocalVLLMRWKVSettings | None = None) -> None:
        self.settings = settings or LocalVLLMRWKVSettings()
        self._base_identity: dict[str, Any] | None = None
        self._last_identity: dict[str, Any] | None = None

    @property
    def model_hash(self) -> str:
        return str(self._load_base_identity()["model_hash"])

    @property
    def feature_dim(self) -> int:
        return int(self._load_base_identity()["hidden_size"])

    def identity(self) -> dict[str, Any]:
        if self._last_identity is not None:
            return dict(self._last_identity)
        return {
            **self._load_base_identity(),
            "feature_protocol": "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
            "pooling": "final-layer-all-real-token-mean",
        }

    def _load_base_identity(self) -> dict[str, Any]:
        if self._base_identity is not None:
            return self._base_identity
        settings = self.settings
        engine_root = settings.engine_root.resolve()
        engine_python = settings.engine_python.absolute()
        model = settings.model.resolve()
        runtime_temp = settings.runtime_temp.resolve()
        if not (engine_root / "vllm/model_executor/models/rwkv7.py").is_file():
            raise RuntimeError(f"missing local vllm-rwkv source tree: {engine_root}")
        revision = _git_value(engine_root, "rev-parse", "HEAD")
        if revision != settings.engine_revision:
            raise RuntimeError(
                "local vllm-rwkv revision mismatch: "
                f"expected={settings.engine_revision} actual={revision}"
            )
        dirty = bool(_git_value(engine_root, "status", "--short"))
        if dirty:
            raise RuntimeError("local vllm-rwkv source tree must be clean")
        if not engine_python.is_file() or not os.access(engine_python, os.X_OK):
            raise RuntimeError(f"missing local vllm-rwkv Python: {engine_python}")
        manifest_path = model / "manifest.json"
        config_path = model / "config.json"
        weights_path = model / "model.safetensors"
        vocab_path = model / "rwkv_vocab_v20230424.txt"
        for path in (manifest_path, config_path, weights_path, vocab_path):
            if not path.is_file():
                raise RuntimeError(f"incomplete local vllm-rwkv model: {path}")
        build_profile_path = engine_root / "vllm/_build_profile.json"
        if not build_profile_path.is_file():
            raise RuntimeError("local vllm-rwkv lacks an immutable build profile")
        build_profile = json.loads(build_profile_path.read_text(encoding="utf-8"))
        if not isinstance(build_profile, Mapping):
            raise RuntimeError("local vllm-rwkv build profile must be an object")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if manifest.get("schema_version") != MODEL_MANIFEST_SCHEMA:
            raise RuntimeError("unsupported local vllm-rwkv model manifest")
        artifact_revision = settings.model_artifact_engine_revision
        if manifest.get("engine", {}).get("revision") != artifact_revision:
            raise RuntimeError("local model artifact engine revision mismatch")
        output = manifest.get("output") or {}
        if output.get("config_sha256") != _file_sha256(config_path):
            raise RuntimeError("local vllm-rwkv config checksum mismatch")
        if output.get("vocab_sha256") != _file_sha256(vocab_path):
            raise RuntimeError("local vllm-rwkv vocabulary checksum mismatch")
        if output.get("weights_sha256") != _file_sha256(weights_path):
            raise RuntimeError("local vllm-rwkv weights checksum mismatch")
        if config.get("architectures") != ["Rwkv7ForCausalLM"]:
            raise RuntimeError("local Router model is not a standard vllm-rwkv artifact")
        runtime_temp.mkdir(parents=True, exist_ok=True)
        environment = self._environment()
        probe = subprocess.run(
            [
                str(engine_python),
                "-c",
                (
                    "import json,torch,transformers,vllm;"
                    "print(json.dumps({'torch':torch.__version__,"
                    "'transformers':transformers.__version__,"
                    "'vllm':vllm.__version__,'module':vllm.__file__}))"
                ),
            ],
            cwd=engine_root,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        versions = json.loads(probe.stdout.splitlines()[-1])
        module_path = Path(versions["module"]).resolve()
        if not module_path.is_relative_to(engine_root):
            raise RuntimeError(f"vllm did not resolve from local source: {module_path}")
        configured_dtype = str(config.get("torch_dtype") or "float16").removeprefix(
            "torch."
        )
        if configured_dtype not in {"float16", "bfloat16"}:
            raise RuntimeError(
                f"unsupported local vllm-rwkv model dtype: {configured_dtype}"
            )
        runtime_derivation: dict[str, Any] | None = None
        if revision != artifact_revision:
            assert settings.runtime_derivation_manifest is not None
            runtime_derivation = _validate_runtime_derivation(
                settings.runtime_derivation_manifest,
                settings.runtime_derivation_manifest_sha256,
                model_manifest_path=manifest_path,
                model_artifact_engine_revision=artifact_revision,
                model_weights_sha256=output["weights_sha256"],
                runtime_engine_root=engine_root,
                runtime_engine_revision=revision,
                runtime_build_profile_sha256=_file_sha256(build_profile_path),
                runtime_source_path=engine_root
                / "vllm/model_executor/models/rwkv7.py",
            )
        base = {
            "backend_version": LOCAL_BACKEND_VERSION,
            "engine_root": str(engine_root),
            "engine_revision": revision,
            "engine_dirty": dirty,
            "engine_python": str(engine_python),
            "vllm_module": str(module_path),
            "vllm_version": versions["vllm"],
            "engine_torch_version": versions["torch"],
            "engine_transformers_version": versions["transformers"],
            "engine_build_profile": dict(build_profile),
            "engine_build_profile_sha256": _file_sha256(build_profile_path),
            "model": str(model),
            "model_manifest_schema": manifest["schema_version"],
            "model_config_sha256": output["config_sha256"],
            "model_weights_sha256": output["weights_sha256"],
            "model_source": manifest["source"],
            "hidden_size": int(config["hidden_size"]),
            "num_hidden_layers": int(config["num_hidden_layers"]),
            "head_size": int(config["head_size"]),
            "vocab_size": int(config["vocab_size"]),
            "tokenizer_class": "RWKVTokenizer",
            "tokenizer_vocab_sha256": output["vocab_sha256"],
            "tokenizer_vocab_size": 65536,
            "bos_token_id": 0,
            "eos_token_id": 0,
            "pad_token_id": 0,
            "truncation_side": "left",
            "max_tokens": settings.max_tokens,
            "wkv_mode": settings.wkv_mode,
            "artifact_dtype": f"torch.{configured_dtype}",
            "runtime_compute_dtype": "torch.float16",
            "dtype": "torch.float16",
            "runtime_temp": str(runtime_temp),
        }
        if runtime_derivation is not None:
            base["model_artifact_engine_revision"] = artifact_revision
            base["runtime_derivation"] = runtime_derivation
        if settings.state_profile_manifest is not None:
            state_manifest = settings.state_profile_manifest.resolve()
            if not state_manifest.is_file():
                raise RuntimeError(
                    f"missing local RWKV state-profile manifest: {state_manifest}"
                )
            actual_manifest_sha256 = _file_sha256(state_manifest)
            if actual_manifest_sha256 != settings.state_profile_manifest_sha256:
                raise RuntimeError(
                    "local RWKV state-profile manifest checksum mismatch"
                )
            base["state_profile"] = {
                "manifest": str(state_manifest),
                "manifest_sha256": actual_manifest_sha256,
                "id": settings.state_profile_id,
                "sha256": settings.state_profile_sha256,
            }
        compatibility_path = model / "runtime_compatibility.json"
        if compatibility_path.is_file():
            if _file_sha256(compatibility_path) != settings.compatibility_sha256:
                raise RuntimeError("local Router compatibility checksum mismatch")
            compatibility = json.loads(
                compatibility_path.read_text(encoding="utf-8")
            )
            if compatibility.get("schema_version") != MODEL_COMPATIBILITY_SCHEMA:
                raise RuntimeError("unsupported local Router compatibility manifest")
            portable = _portable_identity(base)
            if compatibility.get("portable_identity") != portable:
                raise RuntimeError("local Router portable identity mismatch")
            compatibility_hash = str(
                compatibility.get("compatibility_model_hash") or ""
            )
            if len(compatibility_hash) != 64 or any(
                item not in "0123456789abcdef" for item in compatibility_hash
            ):
                raise RuntimeError("invalid local Router compatibility model hash")
            base["portable_identity_digest"] = canonical_digest(portable)
            base["identity_alias_schema"] = MODEL_COMPATIBILITY_SCHEMA
            base["model_hash"] = compatibility_hash
        else:
            base["model_hash"] = canonical_digest(base)
        self._base_identity = base
        return base

    def _environment(self) -> dict[str, str]:
        engine_root = self.settings.engine_root.resolve()
        environment = dict(os.environ)
        existing_pythonpath = environment.get("PYTHONPATH", "")
        environment["PYTHONPATH"] = (
            str(engine_root)
            if not existing_pythonpath
            else f"{engine_root}{os.pathsep}{existing_pythonpath}"
        )
        runtime_temp = str(self.settings.runtime_temp.resolve())
        environment.update(
            {
                "TMPDIR": runtime_temp,
                "TEMP": runtime_temp,
                "TMP": runtime_temp,
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
                "VLLM_RWKV7_WKV_MODE": self.settings.wkv_mode,
            }
        )
        return environment

    def _invoke(
        self,
        operation: str,
        texts: Sequence[str],
        *,
        codes: Sequence[str] = (),
        layer_index: int = -1,
    ) -> tuple[Any, list[int], Mapping[str, Any]]:
        if not texts or any(not str(text).strip() for text in texts):
            raise ValueError("local vllm-rwkv extraction texts must be non-empty")
        base = self._load_base_identity()
        request = {
            "schema_version": WORKER_REQUEST_SCHEMA,
            "operation": operation,
            "texts": [str(text) for text in texts],
            "codes": [str(code) for code in codes],
            "layer_index": layer_index,
            "engine_root": base["engine_root"],
            "model_path": base["model"],
            "runtime_temp": base["runtime_temp"],
            "batch_size": self.settings.batch_size,
            "max_tokens": self.settings.max_tokens,
            "wkv_mode": self.settings.wkv_mode,
        }
        temp_root = ROOT / "temp"
        temp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="state-router-vllm-", dir=temp_root
        ) as directory:
            work = Path(directory)
            request_path = work / "request.json"
            output_path = work / "features.npz"
            request_path.write_text(
                json.dumps(request, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            worker = ROOT / "scripts/state_router_vllm_worker_v1.py"
            completed = subprocess.run(
                [
                    str(self.settings.engine_python.absolute()),
                    str(worker),
                    "--request",
                    str(request_path),
                    "--output",
                    str(output_path),
                ],
                cwd=self.settings.engine_root.resolve(),
                env=self._environment(),
                check=False,
                capture_output=True,
                text=True,
                timeout=3600,
            )
            if completed.returncode != 0:
                detail = "\n".join(
                    (completed.stdout + "\n" + completed.stderr).splitlines()[-30:]
                )
                raise RuntimeError(f"local vllm-rwkv worker failed:\n{detail}")
            response_path = output_path.with_suffix(output_path.suffix + ".json")
            response = json.loads(response_path.read_text(encoding="utf-8"))
            if response.get("schema_version") != WORKER_RESPONSE_SCHEMA:
                raise RuntimeError("unsupported local vllm-rwkv worker response")
            if response.get("operation") != operation or response.get("rows") != len(
                texts
            ):
                raise RuntimeError("local vllm-rwkv worker response identity mismatch")
            import numpy as np

            with np.load(output_path) as archive:
                features = np.asarray(archive["features"], dtype=np.float32).copy()
        if features.ndim != 2 or features.shape[0] != len(texts):
            raise RuntimeError("local vllm-rwkv feature shape mismatch")
        if not bool(np.isfinite(features).all()):
            raise RuntimeError("local vllm-rwkv returned non-finite features")
        token_counts = [int(value) for value in response["token_counts"]]
        if len(token_counts) != len(texts) or not all(
            1 <= value <= self.settings.max_tokens for value in token_counts
        ):
            raise RuntimeError("local vllm-rwkv token counts are invalid")
        runtime = response["runtime"]
        tokenizer = response["tokenizer"]
        comparisons = {
            "vllm_module": runtime["vllm_module"],
            "vllm_version": runtime["vllm_version"],
            "engine_torch_version": runtime["torch_version"],
            "engine_transformers_version": runtime["transformers_version"],
            "hidden_size": runtime["hidden_size"],
            "num_hidden_layers": runtime["num_hidden_layers"],
            "head_size": runtime["head_size"],
            "vocab_size": runtime["vocab_size"],
            "wkv_mode": runtime["wkv_mode"],
            "tokenizer_class": tokenizer["class"],
            "tokenizer_vocab_size": tokenizer["vocab_size"],
            "bos_token_id": tokenizer["bos_token_id"],
            "eos_token_id": tokenizer["eos_token_id"],
            "pad_token_id": tokenizer["pad_token_id"],
            "truncation_side": tokenizer["truncation_side"],
        }
        mismatches = {
            key: {"expected": base[key], "actual": value}
            for key, value in comparisons.items()
            if base[key] != value
        }
        if mismatches:
            raise RuntimeError(f"local vllm-rwkv runtime identity mismatch: {mismatches}")
        protocols = {
            "hidden_mean": (
                "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
                "final-layer-all-real-token-mean",
            ),
            "wkv_statistics": (
                "rwkv-lh.vllm-rwkv-final-wkv-statistics.v1",
                "last-layer-row-column-diagonal-rms",
            ),
            "code_logits": (
                "rwkv-lh.vllm-rwkv-constrained-code-logits.v1",
                "last-token-fp32-lm-head-selected-codes",
            ),
        }
        feature_protocol, extraction = protocols[operation]
        identity = {
            **base,
            "feature_protocol": feature_protocol,
            "extraction": extraction,
            "runtime": runtime,
        }
        self._last_identity = identity
        return features, token_counts, identity

    def score_single_token_codes(
        self,
        prompts: Sequence[str],
        codes: Sequence[str],
    ) -> Any:
        if not codes or len(set(codes)) != len(codes):
            raise ValueError("constrained Router codes must be unique and non-empty")
        features, _, _ = self._invoke("code_logits", prompts, codes=codes)
        import torch

        return torch.from_numpy(features)

    def extract_wkv_statistics(
        self,
        texts: Sequence[str],
        *,
        layer_index: int = -1,
    ) -> tuple[Any, list[int], Mapping[str, Any]]:
        features, token_counts, identity = self._invoke(
            "wkv_statistics", texts, layer_index=layer_index
        )
        import torch

        return torch.from_numpy(features), token_counts, identity
