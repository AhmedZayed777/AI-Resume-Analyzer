from pydantic import BaseModel, Field


class Education(BaseModel):
    degree: str
    institution: str = ""
    year: str = ""


class Experience(BaseModel):
    title: str
    company: str = ""
    duration: str = ""
    highlights: list[str] = Field(default_factory=list)


class ResumeAnalysis(BaseModel):
    full_name: str = ""
    email: str = ""
    technical_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    years_of_experience: float = 0
    summary: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class JobInput(BaseModel):
    id: int
    title: str
    description: str
    required_skills: list[str] = Field(default_factory=list)
    min_years_experience: float = 0


class JobMatch(BaseModel):
    job_id: int
    title: str
    score: float
    matched_skills: list[str]
    missing_skills: list[str]
    explanation: str = ""


class ResumeImprovement(BaseModel):
    missing_skills: list[str]
    weaknesses: list[str]
    improvements: list[str]
    certifications: list[str]
    learning_resources: list[str]