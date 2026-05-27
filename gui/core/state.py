from dataclasses import dataclass, field
from typing import List


@dataclass
class AppState:
    api_url: str = ""
    env_name: str = "正式环境"      # API 环境名称，决定使用哪个 region 文件
    public_key: str = ""
    private_key: str = ""
    project_ids: str = ""          # 逗号分隔的项目ID
    selected_regions: List[str] = field(default_factory=list)
    selected_resources: List[str] = field(default_factory=list)
