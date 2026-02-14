# 論文執筆リポジトリ with AIエージェント

AIエージェント(Claude Codeを想定)とユーザーが対話しながら効率的に論文を仕上げる執筆システム。

```
全体の流れ
(1) refs/ に関連論文・発表スライド・メモ・コードを保存
(2) -> AIに雑誌投稿規定を要約してもらう 
(3) -> AIと相談してアウトラインを作成・更新 
(4) -> アウトラインに基づいてAIと各セクションを書く 
(5) -> 色々とわかってきたら(3)に戻りAIと相談してアウトラインを更新(反復)
```

---

## フォルダ構成

```
paper/
├── author_guidelines/      # 投稿先の公式ガイドラインPDF（ユーザーが配置）
├── AUTHOR_GUIDELINES.md    # AIが抽出した雑誌投稿規定の要約
├── OUTLINE.md              # AIとの共有メモリ：アウトライン + 決定ログ
├── CLAUDE.md               # AIへの指示書
│
├── tex/
│   ├── main.tex            # LaTeX メインファイル
│   ├── sections/           # セクションごとの本文
│   ├── figures/            # 図ファイル
│   └── refs.bib            # 参考文献データベース
│
└── refs/                   # 参考資料置き場（論文PDF、スライド、メモ等）
```

---

## セットアップ

### LaTeX インストール（Mac）

```bash
brew install --cask mactex
```

### MCP サーバー設定（BibTeX自動取得、オプション）

```bash
claude mcp add --transport http bibtex --scope project https://mcp.florianbrand.de/mcp
```

---

## 執筆ワークフロー

### 初回

1. **参考資料を配置**: `refs/` に論文PDF、発表スライド、メモ、コード等を入れる
2. **雑誌投稿規定を配置**: `author_guidelines/` にジャーナルのガイドラインを入れる（投稿先が決まっている場合のみ）
3. **ルール抽出**: `@author_guidelines/ を読んで @AUTHOR_GUIDELINES.md を作成して`（投稿先が決まっている場合のみ）
4. **アウトライン作成**: `@refs/ を読んで @OUTLINE.md を一緒に作成しましょう。AskUserQuestionTool を使って私へ質問して`

### 日々の執筆

1. **OUTLINE.md の相談**: `@OUTLINE.md のイントロダクションだけど、論文全体の問いについて議論してブラッシュアップしましょう。 @refs/ を参考にして`
2. **OUTLINE.md を更新**: `イントロダクションでTODOとして残っている提案手法の新規性だけど、XXXとしましょう`
3. **セクション執筆**: `@OUTLINE.md に基づいて @introduction.tex を更新して。詳しい説明は @refs/ を参考にして`
4. **プレビュー**: 保存で自動ビルド（このリポジトリの VS Code/Cursor + LaTeX Workshop 設定で自動でビルドされます）
5. **必要ならばTeXをマニュアル修正**: 
6. **繰り返す**

### 図の掲載

1. Figureファイルは `tex/figures/` に配置して掲載するように指示: `@figures/fig01.png を @tex/sections/results.tex にFig. 1として掲載して。キャプションを書いて`

---

## よく使う依頼文

| 依頼内容 | 例 |
|---------|-----|
| 投稿規定まとめ | `@author_guidelines/ を読んで @AUTHOR_GUIDELINES.md を更新して`（投稿先が決まっている場合のみ） |
| アウトライン作成 | `@refs/ を読んで @OUTLINE.md を一緒に作成しましょう。AskUserQuestionTool を使って私へ質問して` |
| セクション執筆 | `@OUTLINE.md と @refs/ を使って @introduction.tex を更新して` |
| BibTeX追加 | `/add-bibtex Attention is all you need` |
| エラー修正 | `@build_errors.md を見てエラーを修正して` |

---

## ビルド

### VS Code/Cursor（推奨）

LaTeX Workshop で保存時に自動ビルド。構文警告は Problems パネルに表示される（chktex、MacTeX に含まれる）。

### ターミナルから手動ビルド

```bash
cd tex && pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
```

---

## リンク

- [HenriquesLab bioRxiv template](https://github.com/HenriquesLab/HenriquesLab-bioRxiv-template)
