import base64
import logging
import time
from typing import Optional, Union

from app.core.config import settings

logger = logging.getLogger("edunex.multimodal.vision")

DIAGRAM_SYSTEM_PROMPT = """You are EduNex AI Vision Assistant, an expert educational diagram and visual content analyzer.
Your role is to help students understand visual materials: diagrams, flowcharts, architecture maps, mathematical plots, biological structures, chemical formulas, and network graphs.

When explaining an educational image:
1. Identify the core topic and visual format (e.g., Sequence Diagram, Circuit Schematic, Anatomical Chart, Flowchart).
2. Deconstruct the key labeled elements, symbols, blocks, and connections step-by-step.
3. State the underlying academic concept or physical/logical principle shown.
4. Provide a clear pedagogical explanation with simple analogies where helpful.
5. Highlight exam-relevant takeaways or common pitfalls students encounter with this concept."""

MATH_SYSTEM_PROMPT = """You are EduNex AI Mathematics & STEM Assistant.
Analyze this mathematical illustration, formula, geometric diagram, or coordinate plot:
1. Transcribe any equations or geometric relations into clean LaTeX format ($...$ and $$...$$).
2. Explain the variables, axes, coordinates, or theorem depicted.
3. Provide step-by-step mathematical reasoning or proof of the concept shown.
4. Conclude with a practical computational application."""


class VisionClient:
    """
    Multimodal Vision client leveraging Google Gemini Vision for analyzing educational imagery.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ):
        self.model_name = model_name or settings.GEMINI_MODEL
        self.timeout = timeout_seconds

    async def analyze_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
        prompt: Optional[str] = None,
        prompt_type: str = "diagram",
        extra_context: Optional[str] = None,
    ) -> str:
        """
        Sends image and instructional prompt to Gemini Vision.
        """
        user_prompt = prompt or "Explain this educational diagram and its core components in detail."
        if extra_context:
            user_prompt = f"Context from study materials:\n{extra_context}\n\nStudent Question:\n{user_prompt}"

        system_instruction = MATH_SYSTEM_PROMPT if prompt_type == "math" else DIAGRAM_SYSTEM_PROMPT

        api_key = settings.GOOGLE_API_KEY
        if (
            not api_key
            or not api_key.strip()
            or settings.ENVIRONMENT == "testing"
            or api_key.startswith("test")
            or api_key == "dummy-key-for-test"
        ):
            logger.info("Using offline educational vision response engine (test/offline mode).")
            return self._generate_offline_vision_mock(user_prompt, prompt_type)

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)

            part = types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type,
            )

            contents = [
                part,
                user_prompt,
            ]

            config = types.GenerateContentConfig(
                temperature=0.2,
                system_instruction=system_instruction,
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )
            return response.text.strip()
        except Exception as e:
            logger.error("Gemini Vision call failed: %s", str(e))
            # If live call fails (e.g. timeout or network unreachable in sandbox), provide diagnostic fallback
            raise RuntimeError(f"Vision analysis failed ({self.model_name}): {str(e)}") from e

    def _generate_offline_vision_mock(self, prompt: str, prompt_type: str) -> str:
        """
        Deterministic pedagogical explanation engine for offline tests and development.
        """
        p_lower = prompt.lower()

        if prompt_type == "math" or "math" in p_lower or "equation" in p_lower or "formula" in p_lower:
            return (
                "### 📐 Mathematical Analysis & Diagram Breakdown\n\n"
                "**1. Visual Identification**: The illustration depicts a mathematical function and geometric relation.\n\n"
                "**2. Formal Formulation**:\n"
                "- Primary Formula: $$\\nabla \\cdot \\mathbf{E} = \\frac{\\rho}{\\varepsilon_0}$$\n"
                "- Geometric Interpretation: Illustrates the divergence of a vector field from positive sources to negative sinks.\n\n"
                "**3. Step-by-Step Derivation**:\n"
                "1. Establish the boundary surface enclosed by the volume integral $\\oint_S \\mathbf{E} \\cdot d\\mathbf{A}$.\n"
                "2. Apply the Divergence Theorem to convert the flux integral into a volume integral $\\int_V (\\nabla \\cdot \\mathbf{E}) dV$.\n"
                "3. Relate total enclosed charge $Q_{enc} = \\int_V \\rho \\, dV$.\n\n"
                "**4. Practical Application**: Used extensively in electromagnetism, fluid dynamics, and electrostatics."
            )

        # Default educational diagram breakdown
        return (
            "### 📊 Educational Diagram Explanation\n\n"
            "**1. Diagram Identification**: High-level educational architectural schematic illustrating component interactions and data flow.\n\n"
            "**2. Key Visual Components**:\n"
            "- **Source / Input Node**: Represents the origin of student requests or input packets.\n"
            "- **Processing Pipeline**: Demonstrates sequential filtering, transformation, and validation stages.\n"
            "- **Output / Feedback Loop**: Closes the communication channel with verified status indicators.\n\n"
            "**3. Core Concept**: The visual demonstrates **layered modularity**—each module operates independently with well-defined interface contracts.\n\n"
            "**4. Real-World Analogy**: Think of it like an automated assembly line where each station inspects and enhances the payload before handing it off to the next station.\n\n"
            "**5. Key Exam Takeaway**: Pay special attention to the directional arrows indicating state flow versus data acknowledgment."
        )
