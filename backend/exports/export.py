import logging
import os
from typing import Any
import uuid

# Graceful import check for pptx and weasyprint
try:
    import pptx
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
except ImportError:
    pptx = None

try:
    import weasyprint
except ImportError:
    weasyprint = None

logger = logging.getLogger("app.exports")


class ExportCompiler:
    """Compiles startup blueprints into professional print documents and presentations."""

    def compile_blueprint_to_html(self, blueprint_data: dict[str, Any]) -> str:
        """Compiles the raw blueprint JSON dataset into a clean, print-ready HTML page."""
        title = blueprint_data.get("executive_summary", {}).get("startup_name") or "Startup Blueprint"
        industry = blueprint_data.get("dna", {}).get("market_opportunity", {}).get("industry") or "SaaS"
        
        # Cover page background and liquid glass style guidelines
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title} - Startup Blueprint</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;800&display=swap');
        
        @page {{
            size: A4;
            margin: 20mm;
            @bottom-right {{
                content: counter(page);
                font-family: 'Inter', sans-serif;
                font-size: 9pt;
                color: #8892b0;
            }}
        }}

        @media print {{
            body {{
                background: #ffffff !important;
                color: #0a192f !important;
            }}
            .page-break {{
                page-break-before: always;
            }}
        }}

        body {{
            font-family: 'Inter', sans-serif;
            color: #1a202c;
            line-height: 1.6;
            background: #fafbfe;
            margin: 0;
            padding: 0;
        }}

        .cover-page {{
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            padding: 40px;
            background: radial-gradient(circle at 10% 20%, rgba(98, 125, 250, 0.05) 0%, rgba(255, 255, 255, 0) 90%);
            page-break-after: always;
        }}

        .cover-title {{
            font-family: 'Outfit', sans-serif;
            font-size: 42pt;
            font-weight: 800;
            color: #0f172a;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .cover-subtitle {{
            font-size: 18pt;
            color: #475569;
            margin-bottom: 40px;
            font-weight: 300;
        }}

        .cover-meta {{
            margin-top: 100px;
            font-size: 11pt;
            color: #64748b;
            border-top: 1px solid #e2e8f0;
            padding-top: 20px;
            width: 80%;
            max-width: 500px;
        }}

        .section {{
            margin-bottom: 40px;
            page-break-inside: avoid;
        }}

        h1 {{
            font-family: 'Outfit', sans-serif;
            font-size: 24pt;
            font-weight: 600;
            color: #1e3a8a;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 8px;
            margin-top: 40px;
            margin-bottom: 20px;
        }}

        h2 {{
            font-family: 'Outfit', sans-serif;
            font-size: 16pt;
            color: #2563eb;
            margin-top: 25px;
            margin-bottom: 15px;
        }}

        p {{
            margin-bottom: 15px;
            text-align: justify;
        }}

        .card {{
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}

        th {{
            background-color: #f8fafc;
            color: #1e293b;
            text-align: left;
            padding: 12px;
            font-weight: 600;
            border-bottom: 2px solid #e2e8f0;
        }}

        td {{
            padding: 12px;
            border-bottom: 1px solid #e2e8f0;
        }}

        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin: 20px 0;
        }}

        .metric-card {{
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }}

        .metric-value {{
            font-size: 20pt;
            font-weight: 700;
            color: #1e3a8a;
        }}

        .metric-label {{
            font-size: 10pt;
            color: #60a5fa;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
    </style>
</head>
<body>
    <div class="cover-page">
        <div style="font-size: 12pt; text-transform: uppercase; letter-spacing: 2px; color: #3b82f6; font-weight: 600; margin-bottom: 20px;">Startup Strategic Blueprint</div>
        <div class="cover-title">{title}</div>
        <div class="cover-subtitle">Strategic, Operational, and Financial Roadmap</div>
        <div class="cover-meta">
            <strong>Industry Vertical:</strong> {industry}<br>
            <strong>Prepared by:</strong> Start-up Evolution Engine<br>
            <strong>Version Snapshot:</strong> 1.0.0<br>
            <strong>Date Generated:</strong> {blueprint_data.get("generation_metadata", {}).get("timestamp", "June 2026")}
        </div>
    </div>

    <div class="section">
        <h1>1. Executive Summary</h1>
        <div class="card">
            <h2>Vision Statement</h2>
            <p>{blueprint_data.get("executive_summary", {}).get("vision", "Not available")}</p>
            <h2>Strategic Direction</h2>
            <p>{blueprint_data.get("executive_summary", {}).get("summary", "Not available")}</p>
        </div>
    </div>
"""

        # Append DNA section if present
        if "startup_dna" in blueprint_data:
            dna = blueprint_data["startup_dna"]
            html += f"""
    <div class="section page-break">
        <h1>2. Startup DNA & Market Validation</h1>
        <div class="card">
            <h2>Value Proposition (USP)</h2>
            <p>{dna.get("value_proposition", {}).get("core_usp", "Not defined")}</p>
            <h2>Revenue Streams</h2>
            <ul>
            """
            for stream in dna.get("revenue_model", {}).get("revenue_streams", []):
                html += f"<li>{stream}</li>"
            html += """
            </ul>
        </div>
    </div>
"""

        # Append Features section if present
        if "product_architecture" in blueprint_data:
            feats = blueprint_data["product_architecture"].get("features", [])
            html += """
    <div class="section page-break">
        <h1>3. Product MVP Feature Catalog</h1>
        <table>
            <thead>
                <tr>
                    <th>Feature Name</th>
                    <th>Category</th>
                    <th>Priority</th>
                    <th>Complexity</th>
                </tr>
            </thead>
            <tbody>
            """
            for feat in feats:
                html += f"""
                <tr>
                    <td><strong>{feat.get("name")}</strong><br><small>{feat.get("description")}</small></td>
                    <td>{feat.get("category")}</td>
                    <td>{feat.get("priority")}</td>
                    <td>{feat.get("complexity")}</td>
                </tr>
                """
            html += """
            </tbody>
        </table>
    </div>
"""

        # Append Team section if present
        if "team_structure" in blueprint_data:
            roles = blueprint_data["team_structure"].get("roles", [])
            html += """
    <div class="section page-break">
        <h1>4. Organizational Structure & Talent plan</h1>
        <table>
            <thead>
                <tr>
                    <th>Role Title</th>
                    <th>Department</th>
                    <th>Estimated Salary (USD/yr)</th>
                    <th>Core Responsibilities</th>
                </tr>
            </thead>
            <tbody>
            """
            for role in roles:
                html += f"""
                <tr>
                    <td><strong>{role.get("role_title")}</strong></td>
                    <td>{role.get("department")}</td>
                    <td>${role.get("salary_range_usd_min", 0):,}/yr - ${role.get("salary_range_usd_max", 0):,}/yr</td>
                    <td>{", ".join(role.get("key_responsibilities", []))}</td>
                </tr>
                """
            html += """
            </tbody>
        </table>
    </div>
"""

        # Append SWOT section if present
        if "swot_analysis" in blueprint_data:
            swot = blueprint_data["swot_analysis"]
            html += f"""
    <div class="section page-break">
        <h1>5. SWOT Analysis</h1>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div class="card" style="border-left: 5px solid #22c55e;">
                <h3 style="color: #22c55e;">Strengths</h3>
                <ul>
            """
            for strength in swot.get("strengths", []):
                html += f"<li>{strength}</li>"
            html += """
                </ul>
            </div>
            <div class="card" style="border-left: 5px solid #ef4444;">
                <h3 style="color: #ef4444;">Weaknesses</h3>
                <ul>
            """
            for weakness in swot.get("weaknesses", []):
                html += f"<li>{weakness}</li>"
            html += """
                </ul>
            </div>
            <div class="card" style="border-left: 5px solid #3b82f6;">
                <h3 style="color: #3b82f6;">Opportunities</h3>
                <ul>
            """
            for opp in swot.get("opportunities", []):
                html += f"<li>{opp}</li>"
            html += """
                </ul>
            </div>
            <div class="card" style="border-left: 5px solid #f59e0b;">
                <h3 style="color: #f59e0b;">Threats</h3>
                <ul>
            """
            for threat in swot.get("threats", []):
                html += f"<li>{threat}</li>"
            html += """
                </ul>
            </div>
        </div>
    </div>
"""

        # Append Costs and Runway section if present
        if "financial_plan" in blueprint_data:
            cost = blueprint_data["financial_plan"]
            html += f"""
    <div class="section page-break">
        <h1>6. Financial Projections & Costs</h1>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-value">${cost.get("funding_requirements", {}).get("minimum_target_usd", 0):,}</div>
                <div class="metric-label">Target Funding</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{cost.get("cash_runway_calculations", {}).get("estimated_runway_months", 0)} Months</div>
                <div class="metric-label">Cash Runway</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">${cost.get("operational_costs", {}).get("annual_operating_expenses_usd", 0):,}</div>
                <div class="metric-label">Annual Operating Exp</div>
            </div>
        </div>
    </div>
"""

        html += """
</body>
</html>
"""
        return html

    def compile_blueprint_to_pdf(self, blueprint_data: dict[str, Any]) -> bytes | None:
        """Compiles the blueprint JSON into binary PDF formats using WeasyPrint if available."""
        if not weasyprint:
            logger.warning("WeasyPrint binary libraries are not available on this runtime environment. Falling back to None.")
            return None

        try:
            html_content = self.compile_blueprint_to_html(blueprint_data)
            pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
            return pdf_bytes
        except Exception as e:
            logger.error("Failed to compile blueprint PDF using WeasyPrint", exc_info=e)
            return None

    def compile_blueprint_to_deck(self, blueprint_data: dict[str, Any]) -> bytes | None:
        """Compiles the blueprint JSON into a PPTX presentation document using python-pptx."""
        if not pptx:
            logger.warning("python-pptx library not found. Falling back to None.")
            return None

        try:
            prs = Presentation()
            
            # Setup slide layouts (0: Title slide, 1: Bullet text slide)
            title_layout = prs.slide_layouts[0]
            bullet_layout = prs.slide_layouts[1]
            blank_layout = prs.slide_layouts[6]

            # 1. Slide 1: Cover Title
            slide1 = prs.slides.add_slide(title_layout)
            title = slide1.shapes.title
            subtitle = slide1.placeholders[1]
            
            title_text = blueprint_data.get("executive_summary", {}).get("startup_name") or "Startup Pitch Deck"
            title.text = title_text
            subtitle.text = "Strategic AI Platform Blueprint\nGenerated by Start-up Evolution Engine"

            # 2. Slide 2: Value Proposition & DNA
            if "dna" in blueprint_data:
                slide2 = prs.slides.add_slide(bullet_layout)
                shapes = slide2.shapes
                title_shape = shapes.title
                title_shape.text = "Value Proposition & Industry Vertical"
                
                body_shape = shapes.placeholders[1]
                tf = body_shape.text_frame
                tf.text = "Core Strategic Value Proposition:"
                
                core_usp = blueprint_data["dna"].get("value_proposition", {}).get("core_usp", "Not Defined")
                p = tf.add_paragraph()
                p.text = f"- USP: {core_usp}"
                p.level = 1
                
                revenue_streams = blueprint_data["dna"].get("revenue_model", {}).get("revenue_streams", [])
                if revenue_streams:
                    p2 = tf.add_paragraph()
                    p2.text = "Primary Revenue Streams:"
                    for stream in revenue_streams[:3]:
                        p_sub = tf.add_paragraph()
                        p_sub.text = f"- {stream}"
                        p_sub.level = 1

            # 3. Slide 3: MVP Features Outline
            if "features" in blueprint_data:
                slide3 = prs.slides.add_slide(bullet_layout)
                shapes = slide3.shapes
                shapes.title.text = "Product MVP Scope & Core Features"
                
                body_shape = shapes.placeholders[1]
                tf = body_shape.text_frame
                tf.text = "Primary Development Focus Features:"
                
                feats = blueprint_data["features"].get("features", [])
                for feat in feats[:5]:
                    p = tf.add_paragraph()
                    p.text = f"- {feat.get('name')} ({feat.get('priority')}): {feat.get('description')[:70]}..."
                    p.level = 1

            # 4. Slide 4: SWOT Matrix Overview
            if "swot" in blueprint_data:
                slide4 = prs.slides.add_slide(bullet_layout)
                shapes = slide4.shapes
                shapes.title.text = "SWOT Matrix Analysis"
                
                body_shape = shapes.placeholders[1]
                tf = body_shape.text_frame
                
                swot = blueprint_data["swot"]
                tf.text = "Strengths & Opportunities:"
                if swot.get("strengths"):
                    p = tf.add_paragraph()
                    p.text = f"- Strength: {swot.get('strengths')[0]}"
                if swot.get("opportunities"):
                    p = tf.add_paragraph()
                    p.text = f"- Opportunity: {swot['opportunities'][0]}"
                    
                p2 = tf.add_paragraph()
                p2.text = "Weaknesses & Threats:"
                if swot.get("weaknesses"):
                    p = tf.add_paragraph()
                    p.text = f"- Weakness: {swot.get('weaknesses')[0]}"
                if swot.get("threats"):
                    p = tf.add_paragraph()
                    p.text = f"- Threat: {swot.get('threats')[0]}"

            # 5. Slide 5: Financial Summary
            if "cost" in blueprint_data:
                slide5 = prs.slides.add_slide(bullet_layout)
                shapes = slide5.shapes
                shapes.title.text = "Operational Costs & Target Runway"
                
                body_shape = shapes.placeholders[1]
                tf = body_shape.text_frame
                
                cost = blueprint_data["cost"]
                target_fund = cost.get("funding_requirements", {}).get("minimum_target_usd", 0)
                runway = cost.get("cash_runway_calculations", {}).get("estimated_runway_months", 0)
                annual_op = cost.get("operational_costs", {}).get("annual_operating_expenses_usd", 0)
                
                tf.text = f"Target Financing: ${target_fund:,}"
                p1 = tf.add_paragraph()
                p1.text = f"- Estimated Cash Runway: {runway} Months"
                p1.level = 1
                p2 = tf.add_paragraph()
                p2.text = f"- Annual Operating Budget: ${annual_op:,}"
                p2.level = 1

            # Save PowerPoint presentation file bytes
            temp_path = f"/tmp/deck-{uuid.uuid4()}.pptx"
            prs.save(temp_path)
            
            with open(temp_path, "rb") as f:
                pptx_bytes = f.read()
                
            os.remove(temp_path)
            return pptx_bytes
            
        except Exception as e:
            logger.error("Failed to compile PowerPoint deck presentation", exc_info=e)
            return None


export_compiler = ExportCompiler()
