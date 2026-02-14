# CLAUDE.md

Claude Code がこのリポジトリで作業する際の指示書。詳細は `README.md` を参照。

## ワークフロー

```
AIと相談してアウトラインを作成・更新 → アウトラインに基づいてAIと各セクションを書く → AIと相談してアウトラインを更新(反復)
```

## ビルド

```bash
cd tex && pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

## 読む順序

1. `AUTHOR_GUIDELINES.md`
2. `OUTLINE.md`
3. `tex/main.tex` → `tex/sections/*.tex`
4. `refs/`

## コアルール

### セクション順（Single Source of Truth）
- セクションの並び順は **`AUTHOR_GUIDELINES.md` の `SECTION_ORDER:` が True**
- 投稿規定により、Methodsが最後など **順番が変わりうる**。必ず `SECTION_ORDER:` を更新してから下記を同期する

### セクション順の同期手順（必ずこの順で）
1. `AUTHOR_GUIDELINES.md` の `SECTION_ORDER:` を更新（ファイル名トークンで管理。例: `methods` → `tex/sections/methods.tex`）
2. `tex/main.tex` の `SECTION ORDER (EDITABLE BY CLAUDE)` ブロック内の `\input{sections/...}` を **`SECTION_ORDER` と同じ順序**に並べ替える（ブロック外は触らない）
3. `OUTLINE.md` の「セクション計画」見出し順も **`SECTION_ORDER` と同じ順序**に並べ替える（内容は保持、順序だけ同期）

### セクション順のチェック項目（事故防止）
- `SECTION_ORDER` の各トークンに対応する `tex/sections/<token>.tex` が存在する
- `tex/main.tex` の `\input{sections/...}` に抜け/重複がない
- `AUTHOR_GUIDELINES.md` / `tex/main.tex` / `OUTLINE.md` で章順が矛盾していない
- `supplementary` は参考文献の後に配置する（`SECTION_ORDER` には入れない）

### OUTLINE.md（共有メモリ）
- 主張、セクション計画、TODO、決定ログを記録
- ユーザーが `.tex` を編集したら `OUTLINE.md` に同期

### 協調的な質問スタイル
**悪い例**: 「この研究の新規性は何ですか？」

**良い例**: 「refs/の資料を読むと、既存手法Xには〇〇という限界があるようです。本研究の新規性として以下が考えられますが、いかがでしょうか？
1. △△を導入することで〇〇を解決
2. □□の観点から新しいアプローチを提案」

- 資料を読んで文脈を理解してから質問
- 選択肢や仮説を提示してユーザーが選びやすくする
- 「こう理解したが合っているか」という確認型で聞く
- ユーザーからの相談にも建設的に対応する
- ユーザーとのコミュニケーションは丁寧に行う

### ジャーナルルール
- ルールを捏造しない
- `author_guidelines/` から `AUTHOR_GUIDELINES.md` を作成

### ファイル配置
- 本文: `tex/sections/*.tex`
- 図: `tex/figures/`
- 参考資料: `refs/`

### 参考文献
- BibTeXを捏造しない
- bibkey形式: `FirstAuthorYYYYShortTitle`
- `/add-bibtex [論文タイトル]` でBibTeX追加

### セクション執筆ガイドライン
- **Abstract**: 単一段落。背景(1文)→問題(1文)→手法(1文)→結果(1-2文)→意義(1文)
- **Introduction**: 広い文脈 → 先行研究 → ギャップ → 本研究の貢献 → 論文構成
- **Methods**: 第三者が再現できる詳細度
- **Results**: 図表と対応させて記述。各結果の解釈を含めて良い
- **Discussion**: 全体を俯瞰した議論。提案手法のメリット・デメリット、生物学的意義、先行研究との比較、限界、今後の展望

### エラー修正
`@build_errors.md を見てエラーを修正して` → `tex/build_errors.md` を読んで対応
