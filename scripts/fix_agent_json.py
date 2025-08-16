#!/usr/bin/env python3
"""
example-agentディレクトリ内のJSONファイルにinstructionフィールドを追加するスクリプト

MDファイルから「- あなたには非常に人間らしい趣味やバックボーンもある。」を含まず、
その次の行から「## 重要事項」の前の行までの内容を抽出してinstructionフィールドとして追加する。
"""

import json
import os
import re
from pathlib import Path


def extract_instruction_from_md(md_file_path):
    """MDファイルからinstruction部分を抽出する"""
    with open(md_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 「- あなたには非常に人間らしい趣味やバックボーンもある。」の行を見つける
    start_pattern = r'- あなたには非常に人間らしい趣味やバックボーンもある。\n'
    start_match = re.search(start_pattern, content)
    
    if not start_match:
        print(f"Warning: 開始パターンが見つかりません: {md_file_path}")
        return None
    
    # 開始位置（次の行から）
    start_pos = start_match.end()
    
    # 「## 重要事項」の前の行までを取得
    end_pattern = r'\n## 重要事項'
    end_match = re.search(end_pattern, content[start_pos:])
    
    if not end_match:
        print(f"Warning: 終了パターンが見つかりません: {md_file_path}")
        return None
    
    # instruction部分を抽出
    instruction = content[start_pos:start_pos + end_match.start()].strip()
    
    return instruction


def fix_json_file(json_file_path, md_file_path):
    """JSONファイルにinstructionフィールドを追加する"""
    # MDファイルからinstruction を抽出
    instruction = extract_instruction_from_md(md_file_path)
    
    if instruction is None:
        print(f"Skipping {json_file_path}: instruction抽出に失敗")
        return False
    
    # JSONファイルを読み込み
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # instructionフィールドを追加
    data['instruction'] = instruction
    
    # JSONファイルに書き戻し（整形して保存）
    with open(json_file_path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Updated: {json_file_path}")
    return True


def main():
    """メイン処理"""
    example_agent_dir = Path(__file__).parent.parent / "example-agent"
    
    if not example_agent_dir.exists():
        print(f"Error: {example_agent_dir} が存在しません")
        return
    
    success_count = 0
    total_count = 0
    
    # example-agentディレクトリ内のJSONファイルを処理
    for json_file in example_agent_dir.glob("*.json"):
        total_count += 1
        
        # 対応するMDファイルのパス
        md_file = json_file.with_suffix('.md')
        
        if not md_file.exists():
            print(f"Warning: 対応するMDファイルが見つかりません: {md_file}")
            continue
        
        # JSONファイルを修正
        if fix_json_file(json_file, md_file):
            success_count += 1
    
    print(f"\n処理完了: {success_count}/{total_count} ファイルが正常に更新されました")


if __name__ == "__main__":
    main()