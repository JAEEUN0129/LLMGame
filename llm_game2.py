import streamlit as st
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import io
import base64
import random
from datetime import datetime
import openai
import os

# OpenAI API 키
openai.api_key = os.getenv("OPENAI_API_KEY")

# -----------------------------
# AI 그림 평가 함수 (수정)
# -----------------------------
def generate_feedback(description, img_bytes):
    # 이미지 base64 인코딩
    buffered = io.BytesIO()
    img_bytes.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    prompt = f"""
당신은 그림 평가 전문가입니다.
사용자가 '{description}'를 그렸습니다.
- 그림의 색상, 구성, 요소를 고려하여 0~10점 사이로 평가하고,
- 점수가 낮은 이유와 개선 방법을 구체적으로 설명해주세요.
점수와 피드백을 JSON으로 반환해주세요.
예시: {{"score":8, "comment":"색감을 조금 더 진하게 해보세요."}}
"""

    try:
        # 최신 SDK 호출 방식
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "친절하고 구체적으로 그림 평가를 해주는 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )
        result_text = response.choices[0].message.content.strip()

        # JSON 파싱 시도
        import json
        try:
            result = json.loads(result_text)
            score = int(result.get("score", 5))  # score 없으면 5점
            comment = result.get("comment", "AI가 코멘트를 제공하지 않았습니다.")
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 fallback
            score = random.randint(3, 8)  # 테스트용 랜덤 점수
            comment = "AI가 JSON 형식으로 응답하지 않아 임의 점수로 평가했습니다."

        # 점수 범위 제한
        score = max(0, min(10, score))
        return score, comment

    except Exception as e:
        # 호출 실패 시 fallback
        print("AI 호출 오류:", e)
        score = random.randint(3, 8)
        comment = "AI 평가 실패, 임의 점수로 평가했습니다."
        return score, comment


# -----------------------------
# 햄버거 레시피 정의
# -----------------------------
burger_recipes = {
    "치즈버거": ["빵", "패티", "치즈"],
    "더블치즈버거": ["빵", "패티", "치즈", "치즈"],
    "새우버거": ["빵", "새우패티", "타르타르소스", "양상추"],
    "불고기버거": ["빵", "불고기패티", "양상추", "소스"],
    "베이컨버거": ["빵", "패티", "베이컨", "치즈", "소스"]
}

# -----------------------------
# 세션 상태 초기화
# -----------------------------
state_vars = ["game_started","start_time","order","buttons_created",
              "current_stack","selected_ingredient","total_score","customers_served"]
for var in state_vars:
    if var not in st.session_state:
        if var == "game_started":
            st.session_state[var] = False
        elif var in ["buttons_created","current_stack"]:
            st.session_state[var] = []
        elif var in ["total_score","customers_served"]:
            st.session_state[var] = 0
        else:
            st.session_state[var] = None

if "canvas_key" not in st.session_state:
    st.session_state.canvas_key = 0

# -----------------------------
# 타이틀 및 게임 방법
# -----------------------------
st.title("🍔 햄버거 스피드 게임 🏃‍♂️")
st.markdown("""
**게임 방법 🍔✨**
1. '손님 주문 받기' 버튼을 눌러 랜덤 주문을 받습니다.
2. 주문 재료를 선택하고 그림판에 그려서 AI 평가 받기 🎨
3. 점수가 충분하면 재료 버튼 생성 완료! (그림 점수가 높을수록 손님 만족도가 높아요!🔥)
4. 버튼을 눌러 햄버거 쌓기 🍔
5. '손님에게 햄버거 드리기' 클릭 시 손님 만족도가 나오고, 한 번 더 클릭하면 다음 주문이 들어옵니다 🎉
6. 제한 시간 3분 내 최대한 많은 손님 만족시키기! 🕒
""")

# -----------------------------
# 게임 시작 버튼
# -----------------------------
if not st.session_state.game_started:
    if st.button("🍔 손님 주문 받기"):
        st.session_state.game_started = True
        st.session_state.order = random.choice(list(burger_recipes.keys()))
        st.session_state.buttons_created = []
        st.session_state.current_stack = []
        st.session_state.selected_ingredient = None
        st.session_state.start_time = datetime.now()
    st.stop()

# -----------------------------
# 제한 시간 계산
# -----------------------------
if st.session_state.start_time:
    time_left = max(0, 180 - int((datetime.now() - st.session_state.start_time).total_seconds()))
else:
    time_left = 180

st.subheader(f"📝 손님 주문: {st.session_state.order}")
st.subheader(f"⏰ 남은 시간: {time_left}초")

if time_left <= 0:
    st.success("⏰ 제한 시간 종료!")
    st.write(f"총 손님: {st.session_state.customers_served}, 총 만족도 점수: {st.session_state.total_score}")
    if st.button("🔄 게임 다시 시작"):
        for var in state_vars:
            if var == "game_started":
                st.session_state[var] = False
            elif var in ["buttons_created","current_stack"]:
                st.session_state[var] = []
            elif var in ["total_score","customers_served"]:
                st.session_state[var] = 0
            else:
                st.session_state[var] = None
        st.session_state.canvas_key = 0
    st.stop()

# -----------------------------
# 재료 선택
# -----------------------------
remaining_ingredients = []
for ing in burger_recipes[st.session_state.order]:
    if ing == "치즈" and st.session_state.order == "더블치즈버거":
        if "치즈" not in st.session_state.buttons_created:
            remaining_ingredients.append("치즈")
    else:
        if ing not in st.session_state.buttons_created:
            remaining_ingredients.append(ing)

if remaining_ingredients:
    st.write("🎨 그릴 재료를 선택하세요.")
    st.session_state.selected_ingredient = st.radio(
        "재료 선택",
        remaining_ingredients
    )

    # -----------------------------
    # 그림 그리기 (색상 선택, 자동 리셋)
    # -----------------------------
    stroke_color = st.color_picker("선 색상 선택", "#000000")
    canvas_result = st_canvas(
        stroke_width=3,
        stroke_color=stroke_color,
        background_color="#ffffff",
        height=300,
        width=400,
        drawing_mode="freedraw",
        key=f"canvas_{st.session_state.canvas_key}"
    )

    if st.button("🖌️ 그림 평가 및 버튼 생성"):
        if canvas_result.image_data is not None:
            img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
            score, comment = generate_feedback(st.session_state.selected_ingredient, img)
            st.session_state.last_score = score
            st.write(f"AI 평가 점수: {score} / 10")
            

            if score >= 4:
                # 더블치즈 특수 처리
                if st.session_state.order == "더블치즈버거" and st.session_state.selected_ingredient == "치즈":
                    st.session_state.buttons_created.extend(["치즈","치즈"])
                else:
                    st.session_state.buttons_created.append(st.session_state.selected_ingredient)
                st.success(f"{st.session_state.selected_ingredient} 버튼 생성 완료!")
            else:
                st.warning("점수가 부족하여 버튼 생성 실패!")

            # 다음 재료 그릴 때 캔버스 자동 리셋
            st.session_state.canvas_key += 1
        else:
            st.warning("먼저 그림을 그려주세요!")

# -----------------------------
# 햄버거 쌓기 버튼
# -----------------------------
if st.session_state.buttons_created:
    st.write("🍔 햄버거 재료 버튼 클릭해서 쌓기")
    for btn in st.session_state.buttons_created:
        if st.button(btn):
            st.session_state.current_stack.append(btn)
            st.write(f"현재 스택: {st.session_state.current_stack}")

# -----------------------------
# 햄버거 완성
# -----------------------------
if st.button("🎉 손님에게 햄버거 드리기"):
    correct_stack = burger_recipes[st.session_state.order]
    if len(st.session_state.current_stack) < 2:
        st.warning("햄버거를 완성하려면 최소 2개의 재료가 필요합니다!")
    elif st.session_state.current_stack[0] != "빵" or st.session_state.current_stack[-1] != "빵":
        st.warning("햄버거는 항상 빵으로 시작하고 끝나야 합니다!")
    else:
        included = all(item in st.session_state.current_stack[1:-1] for item in correct_stack[1:-1])
        if included:
            # 그림 점수 기반 만족도 반영
            satisfaction = int(st.session_state.last_score * 2 + len(st.session_state.current_stack)*2)
            st.session_state.total_score += satisfaction
            st.session_state.customers_served += 1
            st.success(f"손님 만족도 점수: {satisfaction} 🎉")
        else:
            st.warning("햄버거 재료가 주문과 일치하지 않습니다!")

        # 자동으로 다음 손님 주문
        st.session_state.order = random.choice(list(burger_recipes.keys()))
        st.session_state.buttons_created = []
        st.session_state.current_stack = []
        st.session_state.selected_ingredient = None
