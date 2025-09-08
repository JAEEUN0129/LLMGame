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
# AI 그림 평가 함수
# -----------------------------
def generate_feedback(description, img_bytes):
    buffered = io.BytesIO()
    img_bytes.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    prompt = f"""
당신은 그림 평가 전문가입니다.
사용자가 '{description}'를 그렸습니다.

- 그림의 **색상**: 색상이 잘 표현되었는지, 색감이 조화로운지 평가해주세요.
- 그림의 **형태**: 형태가 명확하게 그려졌는지, 흐릿하거나 모호하지 않은지 평가해주세요.
- 그림의 **구성**: 그림의 전체적인 구성이 자연스러운지, 각 요소가 잘 배치되었는지 평가해주세요.
- **상세도**: 세부 사항이 얼마나 잘 그려졌는지 평가해주세요. 너무 단순하거나 자세히 그려졌는지 체크해주세요.
- **주제와 일치 여부**: 주제에 맞게 그려졌는지, 사용자가 그린 그림이 주어진 설명과 일치하는지 평가해주세요.

점수는 0~10점 사이로 매기세요. 각 항목에 대해 간략한 설명을 추가해주세요.
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
        import json
        result = json.loads(result_text)
        score = int(result.get("score", 5))  # score 없으면 5점
        comment = result.get("comment", "AI가 코멘트를 제공하지 않았습니다.")
        return score, comment
    except Exception as e:
        print(f"Error: {e}")
        score = random.randint(3, 8)  # 테스트용 랜덤 점수
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
state_vars = ["game_started", "start_time", "order", "buttons_created",
              "current_stack", "selected_ingredient", "total_score", "customers_served"]
for var in state_vars:
    if var not in st.session_state:
        if var == "game_started":
            st.session_state[var] = False
        elif var in ["buttons_created", "current_stack"]:
            st.session_state[var] = []
        elif var in ["total_score", "customers_served"]:
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
4. 버튼을 눌러 햄버거 쌓기 🍔 (처음과 끝은 항상 빵이 나와야 해요!🥖)
5. '손님에게 햄버거 드리기' 클릭 시 손님 만족도가 나오고, 한 번 더 클릭하면 다음 주문이 들어옵니다 🎉
6. 제한 시간 3분 내 최대한 많은 손님 만족시키기! 🕒

✔️️ 재료 그림을 모두 완성한 후 햄버거를 쌓아야 해요!\n   
✔️ 빵에서 빵으로 안끝나면 다시 재료를 쌓아야 해요!\n
✔️ 모든 재료가 들어가지 않으면 주문이 취소돼요!
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
            elif var in ["buttons_created", "current_stack"]:
                st.session_state[var] = []
            elif var in ["total_score", "customers_served"]:
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
            st.write(f"")

            if score >= 4:
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
        # 재료가 주문과 일치하는지 확인
        included = all(item in st.session_state.current_stack[1:-1] for item in correct_stack[1:-1])
        
        if included:
            # 점수 계산: 그림 점수와 햄버거 완성도 반영
            satisfaction = int(st.session_state.last_score * 2 + len(st.session_state.current_stack) * 2)
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