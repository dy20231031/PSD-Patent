# GitHub 업로드 가이드 (브라우저만 사용)

이 프로젝트에는 `engine/`, `knowledge/`, `.github/`, `.streamlit/`처럼 **폴더 구조가 반드시 유지되어야 하는 파일**이 있습니다.

## 중요

GitHub의 일반 `Upload files` 화면에서 여러 폴더의 파일을 한꺼번에 선택하면 브라우저/선택 방식에 따라 파일 경로가 풀려서
`__init__.py`, `__init__ (1).py`, `__init__ (2).py`처럼 한 폴더에 섞일 수 있습니다.

이 프로젝트는 **GitHub Codespaces에서 ZIP을 업로드한 뒤 압축을 푸는 방식**을 권장합니다.

## 권장 순서

1. GitHub에서 빈 Repository를 생성합니다.
2. Repository의 `Code` → `Codespaces` → `Create codespace on main`을 선택합니다.
3. Codespaces가 열리면 이 배포 ZIP 파일을 왼쪽 File Explorer 영역에 업로드합니다.
4. Codespaces Terminal에서 아래 명령을 실행합니다.

```bash
mkdir -p /tmp/psd-starter
unzip PSD-Patent-Intelligence-starter-v1.1.zip -d /tmp/psd-starter
cp -a /tmp/psd-starter/PSD-Patent-Intelligence/. .
rm PSD-Patent-Intelligence-starter-v1.1.zip
```

5. 파일 구조를 확인합니다.

```bash
find . -maxdepth 3 -type f | sort
```

6. 아래처럼 주요 폴더가 보이면 정상입니다.

```text
.github/
.streamlit/
engine/
knowledge/
sample_data/
tests/
streamlit_app.py
requirements.txt
README.md
```

7. GitHub에 반영합니다.

```bash
git add .
git commit -m "Initial PSD Patent Intelligence project"
git push
```

## 절대 올리지 말아야 하는 파일

- `.streamlit/secrets.toml`
- `.env`
- 실제 OpenAI API Key가 들어 있는 파일

현재 starter에는 실제 API Key가 포함되어 있지 않습니다.
