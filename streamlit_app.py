import streamlit as st
import fitz
import requests
import json
from io import BytesIO
from docx import Document
from fpdf import FPDF

# Page configuration
st.set_page_config(
    page_title="英文学术论文翻译",
    page_icon="📝",
    layout="wide"
)

# Volcano Engine API configuration
VOLCANO_API_ENDPOINT = "https://ark.cn-beijing.volces.com/api/coding"
VOLCANO_API_KEY = "76437c9f-9c6a-4ca4-aee1-47d2971a0db2"


# Functions
def extract_pdf_content(content):
    """Extract text from PDF"""
    doc = fitz.open(stream=content, filetype="pdf")
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n\n"
    return full_text

def split_text_into_chunks(text, chunk_size=2000):
    """Split text into chunks for translation"""
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = para + "\n\n"
        else:
            current_chunk += para + "\n\n"

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks

def create_docx(translated_text):
    """Create DOCX file from translated text"""
    doc = Document()
    paragraphs = translated_text.split('\n\n')
    for para in paragraphs:
        if para.strip():
            doc.add_paragraph(para.strip())
    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    return bio

def create_pdf(translated_text):
    """Create PDF file from translated text"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    paragraphs = translated_text.split('\n\n')
    for para in paragraphs:
        if para.strip():
            try:
                pdf.multi_cell(0, 10, para.strip())
                pdf.ln()
            except:
                pass
    bio = BytesIO()
    pdf.output(dest='S').encode('latin-1', 'ignore')
    bio.write(pdf.output(dest='S').encode('latin-1', 'ignore'))
    bio.seek(0)
    return bio

def translate_chunk(chunk):
    """Translate a single chunk using Volcano Engine API"""

    system_prompt = """你是一位精通中英翻译的资深学术翻译专家，专注于国际关系领域的英文学术论文翻译。

请严格按照以下规则翻译：

1. 严格逐句翻译，保持原文的段落结构不变
2. 语言通顺流利、逻辑精准，严格忠于原文含义，不要添加原文以外的内容，不要演绎
3. 涉及人名和机构名称时：先说中文译文，然后在括号里写明原文英文。格式示例：
   - 正确：美国国会研究服务局（Congressional Research Service）
   - 正确：迈克尔·马斯坦多诺（Michael Mastanduno）
4. 当英文中使用首都指代国家决策者时（如华盛顿指代美国决策者，北京指代中国决策者），请改用中文惯用的国家名称表述：
   - Washington → 美国（当指代决策者时）
   - Beijing → 中国（当指代决策者）
   - Moscow → 俄罗斯
   - London → 英国
   - 保持原文其他地名不变

请直接输出翻译结果，不要添加任何额外说明。"""

    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {VOLCANO_API_KEY}",
            "X-API-Key": VOLCANO_API_KEY
        }


        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"请翻译以下内容：\n\n{chunk}"}
            ],
            "temperature": 0.1
        }

        response = requests.post(VOLCANO_API_ENDPOINT, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        st.error(f"翻译失败: {str(e)}")
        return None

def translate_full_text(text):
    """Translate full text chunk by chunk with progress"""
    chunks = split_text_into_chunks(text)
    translated_chunks = []

    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, chunk in enumerate(chunks):
        status_text.text(f"正在翻译第 {i+1}/{len(chunks)} 段...")
        translation = translate_chunk(chunk)
        if translation:
            translated_chunks.append(translation)
        progress_bar.progress((i + 1) / len(chunks))

    status_text.text("翻译完成！")
    progress_bar.progress(1.0)

    return "\n\n".join(translated_chunks)

# UI
st.title("📝 英文学术论文翻译工具")
st.markdown("### 上传英文PDF论文，获取严格遵循格式规范的中译文本")

st.markdown("""
#### 翻译规范
- ✅ 严格逐句翻译，忠于原文含义
- ✅ 人名机构：中文在前，英文括号在后（例：迈克尔·马斯坦多诺（Michael Mastanduno））
- ✅ 首都指代自动转换：华盛顿 → 美国（指代决策者时）
""")

uploaded_file = st.file_uploader("上传英文PDF论文", type="pdf", help="支持30MB以内的文本格式PDF")

if uploaded_file:
    with st.spinner("正在提取PDF文本..."):
        # Read PDF
        content = uploaded_file.read()
        original_text = extract_pdf_content(content)
        st.success(f"✅ PDF处理完成，共提取 {len(original_text):,} 字符")

        with st.expander("查看提取的原始英文文本"):
            st.text_area("原始文本", original_text, height=200)

    # Start translation
    if st.button("开始翻译", type="primary"):
        translated_text = translate_full_text(original_text)

        if translated_text:
            st.subheader("翻译结果")
            with st.expander("展开查看完整翻译", expanded=True):
                st.markdown(translated_text)

            # Generate all output formats
            base_name = uploaded_file.name.rsplit('.', 1)[0]
            docx_file = create_docx(translated_text)
            pdf_file = create_pdf(translated_text)

            # Download buttons
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.download_button(
                    label="📥 TXT 格式",
                    data=translated_text.encode('utf-8'),
                    file_name=f"{base_name}_中文翻译.txt",
                    mime="text/plain"
                )
            with col2:
                st.download_button(
                    label="📥 Markdown 格式",
                    data=translated_text,
                    file_name=f"{base_name}_中文翻译.md",
                    mime="text/markdown"
                )
            with col3:
                st.download_button(
                    label="📥 Word DOCX 格式",
                    data=docx_file,
                    file_name=f"{base_name}_中文翻译.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            with col4:
                st.download_button(
                    label="📥 PDF 格式",
                    data=pdf_file,
                    file_name=f"{base_name}_中文翻译.pdf",
                    mime="application/pdf"
                )

# Sidebar
with st.sidebar:
    st.header("使用说明")
    st.markdown("""
    1. 点击"上传英文PDF论文"选择文件
    2. 确认文本提取正确后点击"开始翻译"
    3. 等待翻译完成（时间取决于论文长度）
    4. 选择格式下载翻译结果

    **翻译规则**：
    - 严格逐句翻译，不添加额外内容
    - 人名机构：中文 +（原文英文）
    - 首都指代转换为国家名
    """)

    st.divider()

    st.info("""
    💡 提示：翻译时间取决于论文长度，大约每1000词需要30-60秒

    本工具专为国际关系学术论文设计
    """)

# Footer
st.markdown("---")
st.caption("Powered by Volcano Engine Doubao Pro • Built with Streamlit")
