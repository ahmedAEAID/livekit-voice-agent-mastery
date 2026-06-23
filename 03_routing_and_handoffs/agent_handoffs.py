"""Lesson: preserve shared state while handing a call across specialist agents."""

import asyncio
import logging
from dataclasses import dataclass

from livekit import agents, api
from livekit.agents import (
    Agent,
    AgentServer,
    FunctionToolsExecutedEvent,
    MetricsCollectedEvent,
    RunContext,
    function_tool,
    get_job_context,
    metrics,
    room_io,
)
from livekit.agents.llm import ChatContext

from livekit_mastery import create_session

# Set up simple logging
logger = logging.getLogger("Virtual-Real-Estate-Agency")


# Data structure to hold session information
@dataclass
class LeadInfo:
    client_name: str | None = None
    budget: float | None = None
    preferred_area: str | None = None
    choice: str | None = None
    final_price: float | None = None


# ---------------------------------------------------------------------------
# 1. Marwan: The Intake Agent
# ---------------------------------------------------------------------------
class IntakeAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions="""أنت مروان، موظف استقبال ودود جداً ومحترف في وكالة عقارات. 
            مهمتك هي الترحيب بالعميل وجمع 3 معلومات أساسية فقط: اسمه، ميزانيته لشراء العقار، والمنطقة التي يفضلها.
            تحدث باللغة العربية بأسلوب دافئ ومرحب. استخدم الأدوات (tools) المتاحة لك لحفظ هذه البيانات فوراً عندما يذكرها العميل.
            لا تقترح عقارات، فقط اجمع البيانات بلطف."""
        )

    async def on_enter(self) -> None:
        # Await the reply generation
        await self.session.generate_reply(
            instructions="أهلاً بك في وكالتنا العقارية! أنا مروان. عشان أقدر أساعدك تلاقي بيت أحلامك، ممكن تقولي اسم حضرتك إيه؟"
        )

    @function_tool
    async def save_client_name(self, context: RunContext[LeadInfo], name: str):
        """Save the client's name."""
        context.userdata.client_name = name
        logger.info(f"Saved client name: {name}")
        return self._check_handoff(context)

    @function_tool
    async def save_budget(self, context: RunContext[LeadInfo], budget: float):
        """Save the client's budget in numbers."""
        if budget <= 10000:
            return "عذراً، هل يمكنك توضيح الميزانية بشكل أدق؟ نحتاج إلى ميزانية أعلى من 10,000 لنجد لك شيئاً مناسباً."
        context.userdata.budget = budget
        logger.info(f"Saved client budget: {budget}")
        return self._check_handoff(context)

    @function_tool
    async def save_preferred_area(self, context: RunContext[LeadInfo], area: str):
        """Save the client's preferred residential area or city."""
        context.userdata.preferred_area = area
        logger.info(f"Saved preferred area: {area}")
        return self._check_handoff(context)

    def _check_handoff(self, context: RunContext[LeadInfo]):
        data = context.userdata
        # If all 3 pieces of data are collected, hand off to Layla
        if data.client_name and data.budget and data.preferred_area:
            return (
                PropertySpecialist(self.chat_ctx),
                f"ممتاز يا {data.client_name}! سجلت كل البيانات. هحولك حالاً للزميلة ليلى، خبيرة العقارات، عشان تعرض عليك أفضل الخيارات المتاحة.",
            )

        return "شكراً لك. وما هي باقي التفاصيل التي نحتاجها؟"


# ---------------------------------------------------------------------------
# 2. Layla: The Property Specialist
# ---------------------------------------------------------------------------
class PropertySpecialist(Agent):
    def __init__(self, chat_ctx: ChatContext):
        # We define recommendations here just as an example context
        my_recommendations = self.generate_property_recommendations_text()
        super().__init__(
            instructions=f"""أنتِ ليلى، خبيرة عقارات محترفة ولبقة.
            استخدمي المعلومات التي جمعها مروان للتحدث مع العميل بشكل شخصي.
            اعرضي عليه الخيارات المتاحة بأسلوب جذاب. هذه هي الخيارات المتاحة حالياً: {my_recommendations}
            إذا اختار العميل وحدة معينة ووافق على السعر، استخدمي أداة (record_final_choice) لتسجيل اختياره وتحويله للمحامي.""",
            chat_ctx=chat_ctx,
        )

    async def on_enter(self) -> None:
        data = self.session.userdata
        # Await the reply generation
        await self.session.generate_reply(
            instructions=f"أهلاً بك يا {data.client_name}. أنا ليلى. مروان بلغني إن ميزانيتك حوالي {data.budget} وبتدور في منطقة {data.preferred_area}. عندي ليك عروض ممتازة، تحب تسمعها؟"
        )

    def generate_property_recommendations_text(self) -> str:
        """Helper to inject some mock properties into the prompt."""
        return """
        1. فيلا في التجمع الخامس - السعر 5 مليون - 4 غرف.
        2. شقة في الشيخ زايد - السعر 3 مليون - 3 غرف.
        3. شاليه في الساحل - السعر 2 مليون - غرفتين.
        """

    @function_tool
    async def record_final_choice(
        self, context: RunContext[LeadInfo], unit_name: str, price: float
    ):
        """Record the client's final chosen unit and agreed price, then handoff to Legal Agent."""
        context.userdata.choice = unit_name
        context.userdata.final_price = price
        logger.info(f"Recorded final choice: {unit_name} at {price}")

        # Handoff to Adel (Legal Agent) with the chat context preserved
        return (
            LegalAgent(self.chat_ctx),
            f"اختيار رائع جداً! تم تسجيل اختيارك لـ {unit_name} بسعر {price}. سأقوم الآن بتحويلك لأستاذ عادل، المستشار القانوني، لإنهاء إجراءات التعاقد.",
        )


# ---------------------------------------------------------------------------
# 3. Adel: The Legal Agent
# ---------------------------------------------------------------------------
class LegalAgent(Agent):
    def __init__(self, chat_ctx: ChatContext = None):
        super().__init__(
            instructions="""أنت أستاذ عادل، المستشار القانوني في الشركة العقارية.
            تحدث بنبرة رسمية، هادئة، ووقورة.
            راجع مع العميل الوحدة التي اختارها والسعر النهائي بناءً على المحادثة السابقة.
            أخبره بالخطوات القانونية التالية (مثل تجهيز البطاقة الشخصية وتحديد موعد لتوقيع العقود).
            عندما ينتهي العميل من استفساراته، استخدم أداة (end_call) لإنهاء المكالمة.""",
            chat_ctx=chat_ctx,
        )

    async def on_enter(self) -> None:
        data = self.session.userdata
        await self.session.generate_reply(
            instructions=f"أهلاً بك أستاذ {data.client_name}. معك عادل، المستشار القانوني. أهنئك على اختيارك. أنا هنا لمراجعة التفاصيل وتجهيز العقود. هل لديك أي أسئلة قانونية قبل أن نبدأ في الإجراءات؟"
        )

    # @function_tool
    # async def end_call(self, ctx: RunContext):
    #     """Called when the user wants to end the call after everything is settled."""
    #     await ctx.session.generate_reply(instructions="سعدنا بالتعامل معك. سيتم التواصل معك لتحديد موعد التوقيع. مع السلامة.")
    #     await ctx.wait_for_playout() # let the agent finish speaking
    #     await self.hangup_call()
    @function_tool
    async def end_call(self, context: RunContext, reason: str):
        """استخدم هذه الأداة فوراً لإنهاء المكالمة عندما يودعك العميل أو يطلب إغلاق الخط.
        reason: سبب إنهاء المكالمة (مثال: العميل ودعني)."""

        logger.info(f"Triggering hangup. Reason from LLM: {reason}")
        await self.session.say(
            text="سعدنا بالتعامل معك. سيتم التواصل معك لتحديد موعد التوقيع. مع السلامة."
        )
        await context.wait_for_playout()

        # وظيفة في الخلفية تقفل الروم بشكل آمن
        async def delayed_hangup():
            await asyncio.sleep(4)
            ctx = get_job_context()
            if ctx is not None:
                try:
                    logger.info("Attempting to disconnect room...")
                    await ctx.api.room.delete_room(api.DeleteRoomRequest(room=ctx.room.name))
                    logger.info("Room disconnected successfully.")
                except Exception as e:
                    # لو الروم مقفولة بالفعل، هنطبع تحذير بسيط بدل ما نوقع الكود
                    logger.warning(f"Could not delete room (it might be already closed): {e}")

        asyncio.create_task(delayed_hangup())

    async def hangup_call(self):
        ctx = get_job_context()
        if ctx is None:
            return

        await ctx.api.room.delete_room(
            api.DeleteRoomRequest(
                room=ctx.room.name,
            )
        )


# ---------------------------------------------------------------------------
# Agent Server & Session Setup
# ---------------------------------------------------------------------------
server = AgentServer()


@server.rtc_session(agent_name="real_estate_agent")
async def my_agent(ctx: agents.JobContext):
    await ctx.connect()

    # Initialize the session
    session = create_session(
        userdata=LeadInfo(),
        language="ar",
        user_away_timeout=30.0,
    )

    usage_collector = metrics.UsageCollector()

    # --- EVENT LISTENERS ---
    @session.on("function_tools_executed")
    def on_function_tools_executed(event: FunctionToolsExecutedEvent):
        for call, output in event.zipped():
            result = output.output if output else "No output"
            logger.info(f"🛠️ Tool Executed: {call.name} -> {result}")

    @session.on("metrics_collected")
    def on_metrics_collected(event: MetricsCollectedEvent):
        metrics.log_metrics(event.metrics)
        usage_collector.collect(event.metrics)

        if isinstance(event.metrics, metrics.LLMMetrics):
            logger.info(
                f"💰 LLM Cost: {event.metrics.prompt_tokens} prompt + {event.metrics.completion_tokens} completion tokens."
            )
        elif isinstance(event.metrics, metrics.TTSMetrics):
            logger.info(f"⚡ TTS Speed: {event.metrics.ttfb}ms to first byte.")
        elif isinstance(event.metrics, metrics.STTMetrics):
            logger.debug("🎤 STT Activity detected.")

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"📊 Session Summary: {summary}")

    ctx.add_shutdown_callback(log_usage)

    # Start the session with the initial agent
    await session.start(
        room=ctx.room,
        agent=IntakeAgent(),
        room_options=room_io.RoomOptions(),
    )


if __name__ == "__main__":
    agents.cli.run_app(server)
