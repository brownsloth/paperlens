from __future__ import annotations

from dataclasses import dataclass

CORPUS_ID = "real-world-learning"
CORPUS_NAME = "Real World Learning"


@dataclass(frozen=True)
class CorpusPaper:
    paper_id: str
    title_hint: str
    arxiv_id: str | None = None
    pdf_url: str | None = None
    doi: str | None = None
    year: int | None = None
    authors: tuple[str, ...] = ()


REAL_WORLD_LEARNING_PAPERS: list[CorpusPaper] = [
    # 1. Bayesian experimental design
    CorpusPaper("modern-bed", "Modern Bayesian Experimental Design", arxiv_id="2302.14545"),
    CorpusPaper(
        "deep-adaptive-design",
        "Deep Adaptive Design: Amortizing Sequential Bayesian Experimental Design",
        arxiv_id="2103.02438",
    ),
    CorpusPaper(
        "epig-active-learning",
        "Prediction-Oriented Bayesian Active Learning",
        arxiv_id="2304.08151",
    ),
    CorpusPaper(
        "jadai",
        "JADAI: Jointly Amortizing Adaptive Design and Bayesian Inference",
        arxiv_id="2512.22999",
    ),
    # 2. Active learning
    CorpusPaper(
        "llm-active-learning-survey",
        "A Survey of LLM-based Active Learning",
        arxiv_id="2502.11767",
    ),
    CorpusPaper(
        "balsa-benchmark",
        "BALSA: Benchmarking Active Learning Strategies",
        pdf_url="https://openreview.net/pdf/1a6e468c50d6b6fbd49f3a0ca440f857083bd4c4.pdf",
    ),
    # 3. Model-based RL + active exploration
    CorpusPaper(
        "active-exploration-mbrl",
        "Active Exploration in Bayesian Model-based Reinforcement Learning for Robot Manipulation",
        arxiv_id="2404.01867",
    ),
    CorpusPaper(
        "active-exploration-manipulation",
        "Active Exploration for Robotic Manipulation",
        arxiv_id="2210.12806",
    ),
    CorpusPaper(
        "safe-learning-robotics",
        "Safe Learning in Robotics: From Learning-Based Control to Safe Reinforcement Learning",
        arxiv_id="2108.06266",
    ),
    CorpusPaper(
        "safe-active-dynamics",
        "Safe Active Dynamics Learning and Control",
        arxiv_id="2008.11700",
    ),
    CorpusPaper(
        "safe-bayesian-world-models",
        "Safe Exploration Using Bayesian World Models and Log Barriers",
        arxiv_id="2405.05890",
    ),
    # 4. Bayesian optimization + self-driving labs
    CorpusPaper(
        "sdl-tom-review",
        "Self-Driving Laboratories for Chemistry and Materials Science",
        pdf_url="https://europepmc.org/articles/pmc11363023?pdf=render",
        doi="10.1021/acs.chemrev.4c00055",
        year=2024,
        authors=("Gary Tom", "Stefan P. Schmid", "Sterling G. Baird"),
    ),
    CorpusPaper(
        "tobias-sdl-review",
        "Autonomous Self-Driving Laboratories: A Review of Technology and Policy Implications",
        pdf_url="https://pdfs.semanticscholar.org/fb2b/8381b478ae0697727412b3092418e3c70f1b.pdf",
        doi="10.1098/rsos.250646",
        year=2025,
        authors=("Alexander V. Tobias", "Adam Wahab"),
    ),
    CorpusPaper(
        "he-bo-experimental-sciences",
        "Bayesian Optimisation for the Experimental Sciences: A Guide for Experimentalists",
        doi="10.1002/aisy.202501149",
        year=2026,
        authors=("Chuan He", "Martin Singull", "T. Jesper Jacobsson"),
    ),
    CorpusPaper(
        "atlas-sdl",
        "Atlas: A Brain for Self-Driving Laboratories",
        doi="10.1039/D4DD00115J",
        year=2025,
        authors=("Richard J. Hickman",),
    ),
    CorpusPaper(
        "multistage-bo-sdl",
        "Multi-stage Bayesian Optimisation for Dynamic Decision-Making in Self-Driving Labs",
        arxiv_id="2512.15483",
    ),
    CorpusPaper(
        "kusne-materials-discovery",
        "On-the-fly Closed-loop Materials Discovery via Bayesian Active Learning",
        arxiv_id="2006.06141",
    ),
    # 5. LLM agents for scientific discovery
    CorpusPaper(
        "coscientist",
        "Autonomous Chemical Research with Large Language Models (Coscientist)",
        doi="10.1038/s41586-023-06792-0",
        year=2023,
        authors=("Daniil A. Boiko", "Robert MacKnight", "Gabe Gomes"),
    ),
    CorpusPaper(
        "agents-scientific-discovery",
        "Autonomous Agents for Scientific Discovery: Orchestrating Scientists, Language, Code, and Physics",
        arxiv_id="2510.09901",
    ),
    CorpusPaper(
        "llm-scientific-method",
        "Exploring the Role of Large Language Models in the Scientific Method",
        arxiv_id="2505.16477",
    ),
    CorpusPaper(
        "qiushi-discovery-engine",
        "End-to-end Autonomous Scientific Discovery on a Real Optical Platform",
        arxiv_id="2604.27092",
    ),
    # 6. Foundation models for robotics
    CorpusPaper(
        "foundation-models-robotics",
        "Foundation Models in Robotics: Applications, Challenges, and Future Directions",
        arxiv_id="2312.07843",
    ),
    CorpusPaper(
        "embodied-manipulation-fm",
        "Embodied Robot Manipulation in the Era of Foundation Models",
        arxiv_id="2512.22983",
    ),
]

REAL_WORLD_LEARNING_IDS = {p.paper_id for p in REAL_WORLD_LEARNING_PAPERS}
