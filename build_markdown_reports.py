import os
import subprocess
import tempfile
import shutil
import re

# Paths
base_dir = os.path.dirname(os.path.abspath(__file__))
reports = [
    {
        "src": os.path.join(base_dir, "Admin", "admin_system_architecture.md"),
        "dest_pdf": os.path.join(base_dir, "admin_system_architecture.pdf"),
        "title": "คู่มือสถาปัตยกรรมระบบสำหรับผู้ดูแลระบบ (Admin System Architecture)"
    },
    {
        "src": os.path.join(base_dir, "Admin", "testChat", "user_chatbot_architecture.md"),
        "dest_pdf": os.path.join(base_dir, "user_chatbot_architecture.pdf"),
        "title": "คู่มือสถาปัตยกรรมระบบสำหรับผู้ใช้งานทั่วไป (User Chatbot Portal)"
    },
    {
        "src": os.path.join(base_dir, "Admin", "testChat", "chatbot_performance_evaluation.md"),
        "dest_pdf": os.path.join(base_dir, "chatbot_performance_evaluation.pdf"),
        "title": "คู่มือการวัดและประเมินประสิทธิภาพของ Chatbot (RAG Performance Evaluation)"
    }
]

# Locate Edge or Chrome executable
edge_paths = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]
executable = None
for p in edge_paths:
    if os.path.exists(p):
        executable = p
        break
if not executable:
    executable = "msedge"

def get_html_template(title, markdown_content):
    # Escape markdown content to be safe inside HTML and JS script
    # We will embed the raw markdown inside a script tag to avoid escaping issues
    return f"""<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Sarabun:ital,wght@0,300;0,400;0,500;0,700;1,400&family=Outfit:wght@400;600;700&display=swap');
        
        @page {{
            size: A4;
            margin: 20mm 15mm 20mm 15mm;
        }}
        
        * {{ box-sizing: border-box; }}
        
        body {{
            font-family: 'Sarabun', 'Helvetica Neue', Arial, sans-serif;
            color: #334155;
            line-height: 1.6;
            font-size: 14px;
            background-color: #ffffff;
            margin: 0;
            padding: 0;
        }}
        
        #output {{
            padding: 10px;
        }}

        h1, h2, h3, h4, h5, h6 {{
            font-family: 'Outfit', 'Sarabun', sans-serif;
            color: #1e1b4b;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
            font-weight: 700;
        }}
        
        h1 {{
            font-size: 24px;
            border-bottom: 3px solid #0f766e;
            padding-bottom: 10px;
            margin-top: 0;
            color: #0f766e;
        }}
        
        h2 {{
            font-size: 18px;
            border-bottom: 1px solid #cbd5e1;
            padding-bottom: 6px;
            color: #111827;
            margin-top: 2em;
        }}
        
        h3 {{
            font-size: 15px;
            color: #0f766e;
        }}

        p {{
            margin-bottom: 1.2em;
            text-align: justify;
        }}

        ul, ol {{
            margin-bottom: 1.2em;
            padding-left: 20px;
        }}
        
        li {{
            margin-bottom: 0.4em;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 16px 0;
            font-size: 13px;
        }}
        
        th, td {{
            border: 1px solid #cbd5e1;
            padding: 10px 12px;
            text-align: left;
            vertical-align: top;
        }}
        
        th {{
            background-color: #f1f5f9;
            color: #1e293b;
            font-weight: 700;
        }}
        
        tr:nth-child(even) td {{
            background-color: #f8fafc;
        }}

        code {{
            font-family: Consolas, Monaco, monospace;
            background-color: #f1f5f9;
            color: #0f766e;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 13px;
        }}

        pre {{
            background-color: #1e293b;
            color: #f8fafc;
            padding: 16px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 16px 0;
        }}

        pre code {{
            background-color: transparent;
            color: inherit;
            padding: 0;
            border-radius: 0;
            font-size: 13px;
        }}

        .mermaid {{
            display: flex;
            justify-content: center;
            margin: 24px 0;
            padding: 12px;
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            page-break-inside: avoid;
        }}

        .cover-page {{
            page-break-after: always;
            height: 90vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 40px;
            background: linear-gradient(135deg, #0f766e 0%, #115e59 50%, #134e4a 100%);
            color: #ffffff;
            border-radius: 8px;
            margin-bottom: 40px;
        }}

        .cover-title {{
            font-family: 'Outfit', 'Sarabun', sans-serif;
            font-size: 32px;
            font-weight: 700;
            line-height: 1.3;
            margin-bottom: 20px;
        }}

        .cover-subtitle {{
            font-size: 18px;
            color: #ccfbf1;
            margin-bottom: 40px;
        }}

        .cover-meta {{
            border-top: 1px solid rgba(255, 255, 255, 0.2);
            padding-top: 20px;
            font-size: 13px;
            color: #99f6e4;
        }}
    </style>
    <!-- Load marked.js and mermaid.js from CDN -->
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
</head>
<body>
    <div class="cover-page">
        <div style="font-size: 11px; font-weight: 700; letter-spacing: 2px; color: #99f6e4; margin-bottom: 10px; text-transform: uppercase;">
            เอกสารประกอบโครงการพัฒนาแชทบอทอัจฉริยะ (TUH Chatbot AI)
        </div>
        <div class="cover-title">{title}</div>
        <div class="cover-subtitle">โรงพยาบาลธรรมศาสตร์เฉลิมพระเกียรติ</div>
        <div class="cover-meta">
            <div>จัดทำโดย: <strong>ระบบสารสนเทศวิจัยและทดสอบประสิทธิภาพ</strong></div>
            <div>ประเภทเอกสาร: สถาปัตยกรรมระบบและการวิเคราะห์ประสิทธิภาพ</div>
            <div>ปรับปรุงล่าสุด: กรกฎาคม 2569 (2026)</div>
        </div>
    </div>

    <div id="output">กำลังโหลดและจัดรูปแบบเอกสาร...</div>

    <script type="text/markdown" id="markdown-source">
{markdown_content}
    </script>

    <script>
        // Pre-configure mermaid theme to match the report style
        mermaid.initialize({{
            startOnLoad: false,
            theme: 'neutral',
            flowchart: {{
                useWidth: true,
                htmlLabels: true
            }},
            securityLevel: 'loose'
        }});

        // Read markdown content from script block
        const markdownSource = document.getElementById('markdown-source').textContent;

        // Customize marked parser
        marked.use({{
            renderer: {{
                code(code, infostring) {{
                    if (infostring === 'mermaid') {{
                        return `<div class="mermaid">${{code}}</div>`;
                    }}
                    return `<pre><code class="language-${{infostring || 'text'}}">${{code}}</code></pre>`;
                }}
            }}
        }});

        // Render Markdown to HTML
        document.getElementById('output').innerHTML = marked.parse(markdownSource);

        // Run mermaid renderer
        mermaid.run();
    </script>
</body>
</html>
"""

def main():
    print(f"Using executable: {executable}")
    temp_dir = tempfile.gettempdir()
    
    for report in reports:
        src_path = report["src"]
        dest_pdf = report["dest_pdf"]
        title = report["title"]
        
        print(f"\nProcessing: {os.path.basename(src_path)}")
        if not os.path.exists(src_path):
            print(f"Error: Source file {src_path} not found.")
            continue
            
        with open(src_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()
            
        html_layout = get_html_template(title, markdown_content)
        
        temp_html_path = os.path.join(temp_dir, f"{os.path.basename(src_path)}.html")
        temp_pdf_path = os.path.join(temp_dir, f"{os.path.basename(src_path)}.pdf")
        
        # Clean up old temp files
        for p in [temp_html_path, temp_pdf_path]:
            if os.path.exists(p):
                try: os.remove(p)
                except: pass
                
        with open(temp_html_path, "w", encoding="utf-8") as f:
            f.write(html_layout)
            
        # Compile via Edge/Chrome headless
        cmd = [
            executable,
            "--headless",
            "--disable-gpu",
            f"--print-to-pdf={temp_pdf_path}",
            "--no-margins",
            "--print-to-pdf-no-header",
            "--virtual-time-budget=6000",
            temp_html_path
        ]
        
        try:
            print(f"Generating PDF for {title}...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
            
            if os.path.exists(temp_pdf_path):
                # Copy to final destination
                shutil.copy2(temp_pdf_path, dest_pdf)
                print(f"✅ Success! Saved PDF to: {dest_pdf}")
                
                # Also copy to 'pdf/' directory if it exists
                pdf_dir = os.path.join(base_dir, "pdf")
                if os.path.exists(pdf_dir):
                    shutil.copy2(temp_pdf_path, os.path.join(pdf_dir, os.path.basename(dest_pdf)))
                    print(f"✅ Copied copy to: {os.path.join(pdf_dir, os.path.basename(dest_pdf))}")
            else:
                print(f"❌ Failed to generate PDF for {title}.")
                print("STDOUT:", result.stdout)
                print("STDERR:", result.stderr)
        except Exception as e:
            print(f"❌ Error compiling PDF: {e}")
        finally:
            # Cleanup temp files
            for p in [temp_html_path, temp_pdf_path]:
                if os.path.exists(p):
                    try: os.remove(p)
                    except: pass
                    
    print("\nAll tasks completed.")

if __name__ == "__main__":
    main()
