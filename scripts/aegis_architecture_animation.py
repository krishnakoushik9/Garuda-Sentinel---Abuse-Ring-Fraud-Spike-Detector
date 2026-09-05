from manim import *

class AegisArchitecture(Scene):
    def construct(self):
        self.camera.background_color = "#0B0C10"
        
        # ---------------------------------------------------------
        # SECTION 1: Introduction & High-Level Overview
        # ---------------------------------------------------------
        title = Text("AEGIS Sentinel", font_size=64, weight=BOLD, color=BLUE)
        subtitle = Text("Enterprise AI Fraud Defense Architecture", font_size=32, color=GRAY)
        subtitle.next_to(title, DOWN)
        
        self.play(Write(title))
        self.play(FadeIn(subtitle, shift=UP))
        self.wait(2)
        self.play(FadeOut(title), FadeOut(subtitle))

        # ---------------------------------------------------------
        # SECTION 2: Frontend -> Middleware -> Backend (REST API)
        # ---------------------------------------------------------
        section_title = Text("1. The Core Application Flow", font_size=40, color=YELLOW).to_edge(UP)
        self.play(Write(section_title))

        # UI
        ui_box = Rectangle(width=3, height=2, color=CYAN, fill_opacity=0.1)
        ui_text = Text("React + Vite UI\n(Investigator Workstation)", font_size=24).move_to(ui_box.get_center())
        ui_group = VGroup(ui_box, ui_text).to_edge(LEFT, buff=1)

        # API Backend
        api_box = Rectangle(width=3, height=2, color=GREEN, fill_opacity=0.1)
        api_text = Text("FastAPI Backend\n(REST Middle-tier)", font_size=24).move_to(api_box.get_center())
        api_group = VGroup(api_box, api_text).to_edge(RIGHT, buff=1)

        arrow_rest = Arrow(ui_group.get_right(), api_group.get_left(), buff=0.2, color=WHITE)
        rest_label = Text("REST API / JSON", font_size=20, color=GRAY).next_to(arrow_rest, UP)

        self.play(Create(ui_group))
        self.wait(1)
        self.play(GrowArrow(arrow_rest), FadeIn(rest_label))
        self.play(Create(api_group))
        self.wait(3)

        self.play(FadeOut(ui_group), FadeOut(arrow_rest), FadeOut(rest_label))
        self.play(api_group.animate.move_to(LEFT * 4))

        # ---------------------------------------------------------
        # SECTION 3: The Data Layer (Redis, SQLite, Neo4j, Kafka)
        # ---------------------------------------------------------
        section_title_2 = Text("2. The Hybrid Data Layer", font_size=40, color=YELLOW).to_edge(UP)
        self.play(Transform(section_title, section_title_2))

        # Data components
        redis_box = Cylinder(radius=0.8, height=1.5, color=RED, fill_opacity=0.2)
        redis_text = Text("Redis\n(Velocity/Cache)", font_size=18).move_to(redis_box)
        redis = VGroup(redis_box, redis_text).move_to(RIGHT * 1 + UP * 1.5)

        neo4j_box = Cylinder(radius=0.8, height=1.5, color=BLUE, fill_opacity=0.2)
        neo4j_text = Text("Neo4j\n(Graph DB)", font_size=18).move_to(neo4j_box)
        neo4j = VGroup(neo4j_box, neo4j_text).move_to(RIGHT * 4 + UP * 1.5)

        sqlite_box = Cylinder(radius=0.8, height=1.5, color=GRAY, fill_opacity=0.2)
        sqlite_text = Text("SQLite\n(Core Ledger)", font_size=18).move_to(sqlite_box)
        sqlite = VGroup(sqlite_box, sqlite_text).move_to(RIGHT * 1 + DOWN * 1.5)

        kafka_box = Rectangle(width=3, height=1, color=ORANGE, fill_opacity=0.2)
        kafka_text = Text("Apache Kafka\n(Event Stream)", font_size=18).move_to(kafka_box)
        kafka = VGroup(kafka_box, kafka_text).move_to(RIGHT * 4 + DOWN * 1.5)

        data_layer = VGroup(redis, neo4j, sqlite, kafka)

        self.play(FadeIn(data_layer, shift=LEFT))
        
        # Connect API to Data
        lines = VGroup(
            Line(api_group.get_right(), redis.get_left(), color=GRAY),
            Line(api_group.get_right(), sqlite.get_left(), color=GRAY),
            Line(api_group.get_right(), kafka.get_left(), color=GRAY),
        )
        self.play(Create(lines))
        self.wait(4)

        self.play(FadeOut(lines), FadeOut(data_layer), FadeOut(api_group))

        # ---------------------------------------------------------
        # SECTION 4: AI Agents & LangGraph
        # ---------------------------------------------------------
        section_title_3 = Text("3. Multi-Agent AI Orchestration", font_size=40, color=YELLOW).to_edge(UP)
        self.play(Transform(section_title, section_title_3))

        langgraph = Rectangle(width=10, height=5, color=BLUE_E, fill_opacity=0.05).shift(DOWN * 0.5)
        lg_title = Text("LangGraph Orchestrator", font_size=28, color=BLUE).next_to(langgraph, UP, inside=True).shift(DOWN*0.2)
        
        # 5 Nodes
        nodes = VGroup(
            Circle(radius=0.7, color=PURPLE, fill_opacity=0.2),
            Circle(radius=0.7, color=PURPLE, fill_opacity=0.2),
            Circle(radius=0.7, color=PURPLE, fill_opacity=0.2),
            Circle(radius=0.7, color=PURPLE, fill_opacity=0.2),
            Circle(radius=0.7, color=PURPLE, fill_opacity=0.2)
        ).arrange(RIGHT, buff=0.8).move_to(langgraph.get_center())

        labels = ["Graph\nAgent", "Temporal\nAgent", "Behavior\nAgent", "Risk\nFusion", "Explain\nAgent"]
        node_labels = VGroup(*[Text(label, font_size=16).move_to(nodes[i].get_center()) for i, label in enumerate(labels)])

        self.play(Create(langgraph), Write(lg_title))
        self.play(FadeIn(nodes, shift=UP), FadeIn(node_labels))

        # Arrows between nodes
        arrows = VGroup(*[Arrow(nodes[i].get_right(), nodes[i+1].get_left(), buff=0.1, color=WHITE) for i in range(4)])
        self.play(Create(arrows))

        # Groq LLM
        groq_box = Rectangle(width=2, height=1, color=PINK, fill_opacity=0.2).next_to(langgraph, DOWN, buff=0.5)
        groq_text = Text("Groq LLM API\n(llama-3.3-70b)", font_size=20).move_to(groq_box)
        groq = VGroup(groq_box, groq_text)

        groq_arrow = Arrow(nodes[-1].get_bottom(), groq.get_top(), color=PINK)
        
        self.play(FadeIn(groq, shift=UP), GrowArrow(groq_arrow))
        self.wait(5)

        self.play(FadeOut(langgraph), FadeOut(lg_title), FadeOut(nodes), FadeOut(node_labels), FadeOut(arrows), FadeOut(groq), FadeOut(groq_arrow))

        # ---------------------------------------------------------
        # SECTION 5: COBOL Mainframe & Kafka Bridge
        # ---------------------------------------------------------
        section_title_4 = Text("4. The COBOL Mainframe Bridge", font_size=40, color=YELLOW).to_edge(UP)
        self.play(Transform(section_title, section_title_4))

        # Python Router
        py_router = Rectangle(width=2.5, height=2, color=GREEN, fill_opacity=0.2).to_edge(LEFT, buff=1)
        py_text = Text("FastAPI\nCOBOL Router", font_size=20).move_to(py_router)
        py_group = VGroup(py_router, py_text)

        # Kafka Topic
        k_topic = Rectangle(width=3, height=1.5, color=ORANGE, fill_opacity=0.2).move_to(ORIGIN)
        k_text = Text("Kafka Topic\nsentinel-risk-events", font_size=20).move_to(k_topic)
        k_group = VGroup(k_topic, k_text)

        # COBOL Daemon
        cbl_daemon = Rectangle(width=2.5, height=2, color=YELLOW, fill_opacity=0.2).to_edge(RIGHT, buff=1)
        cbl_text = Text("GnuCOBOL\nMainframe Binary", font_size=20).move_to(cbl_daemon)
        cbl_group = VGroup(cbl_daemon, cbl_text)

        a1 = Arrow(py_group.get_right(), k_group.get_left(), color=WHITE)
        a2 = Arrow(k_group.get_right(), cbl_group.get_left(), color=WHITE)
        
        # Decision Loop
        k_dec = Rectangle(width=3, height=1.5, color=ORANGE, fill_opacity=0.2).move_to(DOWN*2.5)
        k_dec_text = Text("Kafka Topic\nsentinel-decisions", font_size=20).move_to(k_dec)
        k_dec_group = VGroup(k_dec, k_dec_text)

        a3 = Arrow(cbl_group.get_bottom(), k_dec_group.get_right(), color=WHITE, path_arc=-1)
        a4 = Arrow(k_dec_group.get_left(), py_group.get_bottom(), color=WHITE, path_arc=-1)

        self.play(Create(py_group))
        self.play(GrowArrow(a1), Create(k_group))
        self.play(GrowArrow(a2), Create(cbl_group))
        
        explanation = Text("Deterministic rules override AI decisions", font_size=24, color=WHITE).next_to(cbl_group, UP)
        self.play(Write(explanation))
        self.wait(2)

        self.play(Create(k_dec_group), GrowArrow(a3))
        self.play(GrowArrow(a4))
        self.wait(4)

        self.play(
            FadeOut(py_group), FadeOut(k_group), FadeOut(cbl_group), FadeOut(k_dec_group),
            FadeOut(a1), FadeOut(a2), FadeOut(a3), FadeOut(a4), FadeOut(explanation), FadeOut(section_title)
        )

        # ---------------------------------------------------------
        # SECTION 6: Outro
        # ---------------------------------------------------------
        outro_title = Text("AEGIS Sentinel", font_size=64, weight=BOLD, color=BLUE)
        outro_sub = Text("Securing the Future with AI + Mainframe", font_size=32, color=GRAY).next_to(outro_title, DOWN)
        
        self.play(Write(outro_title))
        self.play(FadeIn(outro_sub, shift=UP))
        self.wait(3)
        
        self.play(FadeOut(outro_title), FadeOut(outro_sub))
        self.wait(1)
