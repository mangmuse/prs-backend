"""회귀 분석용 통계 함수"""

from scipy.stats import ttest_rel


def calculate_p_value(base_scores: list[float], target_scores: list[float]) -> float:
    """
    Paired t-test로 두 Run의 semantic score 차이 유의성 계산.

    Returns:
        p-value (0~1). 낮을수록 유의미한 차이.
        계산 불가 시 1.0 반환 (유의미하지 않음으로 처리).
    """
    if len(base_scores) < 2 or len(target_scores) < 2:
        return 1.0

    if len(base_scores) != len(target_scores):
        return 1.0

    try:
        _, p_value = ttest_rel(base_scores, target_scores)
        if p_value != p_value:  # NaN check (모든 차이가 0인 경우)
            return 1.0
        return float(p_value)
    except Exception:
        return 1.0
