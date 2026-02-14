import os

# 新的 GitHub Actions 配置文件内容
# 变化：
# 1. 显式指定使用 Gradle 8.2 (不再依赖仓库里的 gradlew)
# 2. 将命令从 ./gradlew 改为 gradle
NEW_WORKFLOW = """name: Android CI

on:
  push:
    branches: [ "main" ]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: set up JDK 17
      uses: actions/setup-java@v3
      with:
        java-version: '17'
        distribution: 'temurin'

    - name: Setup Gradle
      uses: gradle/gradle-build-action@v2
      with:
        gradle-version: 8.2

    - name: Build with Gradle
      run: gradle assembleDebug --stacktrace

    - name: Upload APK
      uses: actions/upload-artifact@v4
      with:
        name: app-debug
        path: app/build/outputs/apk/debug/app-debug.apk
"""

def fix_workflow():
    path = ".github/workflows/android.yml"
    
    # 确保目录存在
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(NEW_WORKFLOW)
    
    print(f"✅ 已成功修复 {path}")
    print("-----------------------------------------------------")
    print("👉 请执行以下命令提交更改并重新触发编译：")
    print("   git add .github/workflows/android.yml")
    print("   git commit -m 'Fix CI: Use system gradle instead of wrapper'")
    print("   git push")
    print("-----------------------------------------------------")

if __name__ == "__main__":
    fix_workflow()