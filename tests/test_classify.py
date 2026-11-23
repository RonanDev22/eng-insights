import pytest

from eng_insights.ingestion.classify import is_generated_path


@pytest.mark.parametrize(
    "path",
    [
        "package-lock.json",
        "web/yarn.lock",
        "pnpm-lock.yaml",
        "poetry.lock",
        "apps/api/go.sum",
        "Cargo.lock",
        "Gemfile.lock",
        "uv.lock",
        "static/app.min.js",
        "static/site.min.css",
        "static/app.js.map",
        "node_modules/left-pad/index.js",
        "services/web/node_modules/x/y.js",
        "dist/bundle.js",
        "src/vendor/lib.py",
        "build/out.txt",
        "api/v1/service_pb2.py",
        "api/service.pb.go",
        "pkg/__pycache__/a.cpython-312.pyc",
        ".venv/bin/python",
        "ui/.next/cache.json",
        "web\\node_modules\\x.js",
    ],
)
def test_generated_paths(path):
    assert is_generated_path(path) is True


@pytest.mark.parametrize(
    "path",
    [
        "src/app.py",
        "package.json",
        "README.md",
        "docs/lockfile-notes.md",
        "src/builder.py",
        "src/distribution/a.py",
        "build",
        "dist",
        "src/minify.js",
        "mapper.py",
        "Node_Modules/x.js",
    ],
)
def test_normal_paths(path):
    assert is_generated_path(path) is False
