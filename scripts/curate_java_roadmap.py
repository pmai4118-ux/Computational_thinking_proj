"""Reproduce the link-only Java learning catalog researched on 2026-11-27.

No course text, answers or proprietary assignments are copied. Public reading
availability is separate from enrollment, certificates and cloud lab charges.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFIED = "2026-11-27"
resources: list[dict] = []


def resource(key: str, title: str, url: str, provider: str, kind: str = "documentation",
             *, date: str | None = None, updated: str | None = None, edition: str = "rolling_checked_2026",
             language: str = "en", note: str = "Public page content inspected; enrollment and execution were not tested.") -> str:
    resources.append(dict(id=key, title=title, url=url, provider=provider, kind=kind,
        access="free_reading", language=language, edition=edition, publication_date=date,updated_date=updated,
        verified_at=VERIFIED, verification_note=note,
        rights_note="Link and original catalog metadata only; publisher retains rights to source content."))
    return key


# Exact URLs with readable content observed through the browser research tool.
resource("java-start", "Getting Started with Java", "https://dev.java/learn/first-steps/first-java-code/getting-started/", "Oracle / Dev.java", "guided_tutorial")
resource("java-shell", "JShell — The Java Shell Tool", "https://dev.java/learn/first-steps/first-java-code/jshell-tool/", "Oracle / Dev.java")
resource("java-basics", "Java Language Basics", "https://dev.java/learn/language/constructs/basics/", "Oracle / Dev.java", "tutorial_path")
resource("java-strings", "Numbers and Strings", "https://dev.java/learn/language/constructs/numbers-strings/", "Oracle / Dev.java", "tutorial_path")
resource("java-classes", "Classes and Objects", "https://dev.java/learn/language/oop/classes-objects/", "Oracle / Dev.java", "tutorial_path")
resource("java-records", "Using Records to Model Immutable Data", "https://dev.java/learn/language/oop/records/", "Oracle / Dev.java")
resource("java-inheritance", "Inheritance", "https://dev.java/learn/language/oop/inheritance/", "Oracle / Dev.java", "tutorial_path")
resource("java-interfaces", "Interfaces", "https://dev.java/learn/language/oop/interfaces/", "Oracle / Dev.java", "tutorial_path")
resource("java-generics", "Generics", "https://dev.java/learn/language/fp/generics/", "Oracle / Dev.java", "tutorial_path")
resource("java-lambda", "Lambda Expressions", "https://dev.java/learn/language/fp/lambdas/", "Oracle / Dev.java", "tutorial_path")
resource("java-exceptions", "Exceptions", "https://dev.java/learn/language/annotations-exceptions/exceptions/", "Oracle / Dev.java", "tutorial_path")
resource("java-collections", "The Collections Framework", "https://dev.java/learn/api/collections-and-streams/collections-framework/", "Oracle / Dev.java", "tutorial_path")
resource("java-streams", "The Stream API", "https://dev.java/learn/api/collections-and-streams/streams/", "Oracle / Dev.java", "tutorial_path")
resource("java-time", "The Date Time API", "https://dev.java/learn/api/date-time-regex/date-time/", "Oracle / Dev.java", "tutorial_path")
resource("java-virtual", "Virtual Threads", "https://dev.java/learn/api/virtual-threads/", "Oracle / Dev.java", updated="2026-05-10", note="Page explicitly reports last update May 10, 2026; examples include version-specific pinning differences.")
resource("java-tools", "The Core JDK Tools", "https://dev.java/learn/jvm/core-tools/", "Oracle / Dev.java", "tutorial_path")
resource("java-jfr", "JFR, Monitoring and Troubleshooting", "https://dev.java/learn/jvm/monitoring-troubleshooting/", "Oracle / Dev.java", "tutorial_path")
resource("java-object", "Object: equals and hashCode API", "https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Object.html", "Oracle", edition="Java SE 21 reference; not claimed published in 2024")
resource("java-money", "BigDecimal API", "https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/math/BigDecimal.html", "Oracle", edition="Java SE 21 reference; not claimed published in 2024")
resource("java-concurrency", "java.util.concurrent API", "https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/concurrent/package-summary.html", "Oracle", edition="Java SE 21 reference; not claimed published in 2024")
resource("maven", "Maven in 5 Minutes", "https://maven.apache.org/guides/getting-started/maven-in-five-minutes.html", "Apache Maven", "guided_tutorial")
resource("vscode", "Getting Started with Java in VS Code", "https://code.visualstudio.com/docs/java/java-tutorial", "Microsoft", "guided_tutorial")
resource("http", "Overview of HTTP", "https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview", "MDN")
resource("http-methods", "HTTP request methods", "https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods", "MDN")
resource("http-status", "HTTP response status codes", "https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status", "MDN")
for key, title, slug in [
    ("mit-testing", "Testing", "02-testing"), ("mit-spec", "Specifications", "04-specifications"),
    ("mit-adt", "Abstract Data Types", "06-abstract-data-types"),
    ("mit-invariant", "Abstraction Functions & Rep Invariants", "07-abstraction-functions-rep-invariants"),
    ("mit-concurrency", "Concurrency", "14-concurrency"), ("mit-locks", "Mutual Exclusion", "16-mutual-exclusion")]:
    resource(key, "MIT 6.102: " + title, f"https://web.mit.edu/6.102/www/sp24/classes/{slug}/", "MIT", "course_reading",
             edition="Spring 2024", language="en; TypeScript examples",
             note="2024 course archive inspected. General software-construction material, NOT a Java or Spring course. Embedded tutor may require access; public reading remains usable.")
for key, title, number in [("sql-query", "Querying", 0), ("sql-relations", "Relating", 1), ("sql-design", "Designing", 2), ("sql-index", "Optimizing", 5)]:
    resource(key, "CS50 SQL: " + title, f"https://cs50.harvard.edu/sql/notes/{number}/", "Harvard CS50", "course_reading",
             edition="2024 entry redirects to maintained public OCW",
             note=f"Opened /sql/2024/notes/{number}/; redirects to this maintained public page. Original publication date is not inferred from redirect.")
    resource(key + "-pset", "CS50 SQL Problem Set " + str(number), f"https://cs50.harvard.edu/sql/psets/{number}/", "Harvard CS50", "official_exercise",
             edition="2024 entry redirects to maintained public OCW", note="Public assignment statement inspected; submission/gradebook may require an account.")
resource("sql-final", "CS50 SQL Final Project", "https://cs50.harvard.edu/sql/project/", "Harvard CS50", "official_exercise", edition="2024 entry redirects to maintained public OCW")
resource("postgres", "PostgreSQL Tutorial", "https://www.postgresql.org/docs/16/tutorial.html", "PostgreSQL", edition="PostgreSQL 16 maintained reference")
resource("isolation", "Transaction Isolation", "https://www.postgresql.org/docs/16/transaction-iso.html", "PostgreSQL", edition="PostgreSQL 16 maintained reference")
resource("db-locks", "Explicit Locking and Deadlocks", "https://www.postgresql.org/docs/16/explicit-locking.html", "PostgreSQL", edition="PostgreSQL 16 maintained reference")
for key, title, slug in [
    ("boot-lab", "Building an Application with Spring Boot", "spring-boot"),
    ("rest-lab", "Building a RESTful Web Service", "rest-service"),
    ("validation-lab", "Validating Form Input", "validating-form-input"),
    ("jpa-lab", "Accessing Data with JPA", "accessing-data-jpa"),
    ("mysql-lab", "Accessing data with MySQL", "accessing-data-mysql"),
    ("tx-lab", "Managing Transactions", "managing-transactions"),
    ("security-lab", "Securing a Web Application", "securing-web"),
    ("testing-lab", "Testing the Web Layer", "testing-web"),
    ("client-lab", "Consuming a RESTful Web Service", "consuming-rest"),
    ("breaker-lab", "Spring Cloud Circuit Breaker Guide", "cloud-circuit-breaker"),
    ("mq-lab", "Messaging with RabbitMQ", "messaging-rabbitmq"),
    ("batch-lab", "Creating a Batch Service", "batch-processing"),
    ("schedule-lab", "Scheduling Tasks", "scheduling-tasks"),
    ("docker-lab", "Spring Boot with Docker", "spring-boot-docker"),
    ("actuator-lab", "Building a RESTful Web Service with Spring Boot Actuator", "actuator-service"),
    ("discovery-lab", "Service Registration and Discovery", "service-registration-and-discovery")]:
    resource(key, title, f"https://spring.io/guides/gs/{slug}/", "Spring", "guided_tutorial")
resource("rest-tutorial", "Building REST services with Spring", "https://spring.io/guides/tutorials/rest/", "Spring", "guided_tutorial")
resource("ioc", "The IoC Container", "https://docs.spring.io/spring-framework/reference/core/beans.html", "Spring")
resource("config", "Externalized Configuration", "https://docs.spring.io/spring-boot/reference/features/external-config.html", "Spring")
resource("jdbc", "Data Access with JDBC", "https://docs.spring.io/spring-framework/reference/data-access/jdbc.html", "Spring")
resource("jpa-query", "JPA Query Methods", "https://docs.spring.io/spring-data/jpa/reference/jpa/query-methods.html", "Spring")
resource("transaction", "Using @Transactional", "https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html", "Spring")
resource("security", "Spring Security Architecture", "https://docs.spring.io/spring-security/reference/servlet/architecture.html", "Spring")
resource("jwt", "OAuth 2.0 Resource Server JWT", "https://docs.spring.io/spring-security/reference/servlet/oauth2/resource-server/jwt.html", "Spring")
resource("owasp", "REST Security Cheat Sheet", "https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html", "OWASP")
resource("boot-test", "Spring Boot Testing", "https://docs.spring.io/spring-boot/reference/testing/index.html", "Spring")
resource("junit", "JUnit User Guide", "https://docs.junit.org/6.1.3/overview.html", "JUnit", edition="JUnit 6.1.3; use the version managed by the chosen Spring Boot BOM")
resource("testcontainers", "JUnit 5 Quickstart", "https://java.testcontainers.org/quickstart/junit_5_quickstart/", "Testcontainers", "guided_tutorial")
resource("rest-client", "REST Clients", "https://docs.spring.io/spring-framework/reference/integration/rest-clients.html", "Spring")
resource("cache", "Cache Abstraction", "https://docs.spring.io/spring-framework/reference/integration/cache.html", "Spring")
resource("cache-lab", "Caching Data with Spring", "https://github.com/spring-guides/gs-caching", "Spring", "guided_tutorial", note="Official guide repository/README inspected; spring.io guide URL returned 404, so this working source is used.")
resource("redis", "Redis data types", "https://redis.io/docs/latest/develop/data-types/", "Redis")
resource("docker", "What is a container?", "https://docs.docker.com/learn/content/what-is-a-container/", "Docker", date="2026-10-21")
resource("ci", "Building and testing Java with Maven", "https://docs.github.com/en/actions/tutorials/build-and-test-code/java-with-maven", "GitHub / Microsoft", "guided_tutorial", note="Reading is public; Actions execution can be metered depending on repository/account. Local Maven is the free default practice.")
resource("observability", "Spring Boot Observability", "https://docs.spring.io/spring-boot/reference/actuator/observability.html", "Spring")
resource("otel", "Java OpenTelemetry: Getting Started by Example", "https://opentelemetry.io/docs/languages/java/getting-started/", "OpenTelemetry", "guided_tutorial")
resource("petclinic", "Spring Petclinic sample application", "https://github.com/spring-projects/spring-petclinic", "Spring", "reference_project", note="Official sample repository inspected; read the checked-out LICENSE and pin a commit before redistributing code. This catalog only links to it.")
resource("reactive", "Spring WebFlux", "https://docs.spring.io/spring-framework/reference/web/webflux.html", "Spring")
resource("azure", "Deploy a Spring Boot app to Azure Container Apps", "https://learn.microsoft.com/en-us/training/modules/java-spring-on-azure-container-apps/", "Microsoft Learn", "course_reading", note="Seven-unit learning module is public; Azure resources are NOT guaranteed free. Cloud deployment is optional, never part of the free-only plan.")
resource("blog-boot24", "Bootiful Spring Boot in 2024, part 1", "https://spring.io/blog/2024/03/11/bootiful-spring-boot-in-2024-part-1/", "Spring / Josh Long", "blog", date="2024-03-11")
resource("blog-boot34", "Bootiful Spring Boot 3.4: Spring Boot", "https://spring.io/blog/2024/11/24/bootiful-34-boot/", "Spring / Josh Long", "blog", date="2024-11-24")
resource("blog-mvc26", "Optimizations in Spring MVC", "https://spring.io/blog/2026/02/25/optimizing-spring-mvc/", "Spring / Dave Syer", "blog", date="2026-02-25")
resource("blog-boot4-25", "Modularizing Spring Boot", "https://spring.io/blog/2025/10/28/modularizing-spring-boot/", "Spring Boot Team", "blog", date="2025-10-28")
resource("academy-announcement", "Spring Academy Pro Content Now Free To Access", "https://spring.io/blog/2024/04/10/spring-academy-pro-content-now-free-to-access/", "Spring / Michael Minella", "blog", date="2024-04-10")

for item in resources:
    if item["id"] == "otel":
        item["alternative_url"] = "https://github.com/open-telemetry/opentelemetry.io/blob/main/content/en/docs/languages/java/getting-started.md"
    elif item["id"] == "junit":
        item["alternative_url"] = "https://github.com/junit-team/junit-framework"

courses = [
 dict(id="course-devjava", title="Dev.java learning paths", provider="Oracle / Dev.java", url="https://dev.java/learn/", access="free_public", edition="Maintained; checked 2026", notes="Free public Java reading paths; not a certificate program. Original publication dates vary.", java_specific=True),
 dict(id="course-spring-guides", title="Spring Getting Started Guides", provider="Spring", url="https://spring.io/guides/", access="free_public", edition="Maintained; checked 2026", notes="Public step-by-step Java/Spring guides. This is a guide collection, not a single accredited course.", java_specific=True),
 dict(id="course-microsoft", title="Get started with Java on Azure", provider="Microsoft Learn", url="https://learn.microsoft.com/en-us/training/paths/get-started-java-azure/", access="free_reading_cloud_may_cost", edition="Maintained; checked 2026", notes="Seven modules. Reading is free; Azure subscription/resources may incur costs. Do not default to retired Azure Spring Apps examples.", java_specific=True),
 dict(id="course-mit24", title="6.102 Software Construction", provider="MIT", url="https://web.mit.edu/6.102/www/sp24/", access="free_public", edition="Spring 2024", notes="Public readings and problem statements. Uses TypeScript, NOT Java; included only for transferable testing/specification/concurrency concepts. Tutors and grading may require MIT access.", java_specific=False),
 dict(id="course-harvard", title="CS50 Introduction to Databases with SQL", provider="Harvard", url="https://cs50.harvard.edu/sql/", access="free_public", edition="2024 entry redirects to maintained OCW", notes="Public notes and problem sets; optional verified certificate has separate terms. SQL foundation, not a Java course.", java_specific=False),
 dict(id="course-academy", title="Spring Academy", provider="Spring", url="https://spring.academy/", access="free_registration_announced_2024", edition="Official announcement 2024-04-10", notes="Official 2024 announcement removed Pro subscription for eligible registered email addresses. Current authenticated lab access was not tested; all required lessons have public guide alternatives.", java_specific=True),
 dict(id="course-ibm", title="IBM Java Developer Professional Certificate", provider="IBM / Coursera", url="https://www.coursera.org/professional-certificates/java-developer", access="paid_or_limited_preview", edition="Current catalog checked 2026; publication date not established", notes="Curriculum reference only. Enroll for free is not evidence that full course, graded labs or certificate are free. No subscription/trial is required by this roadmap.", java_specific=True),
 dict(id="course-amazon", title="Amazon Junior Software Developer Professional Certificate", provider="Amazon / Coursera", url="https://www.coursera.org/professional-certificates/amazon-junior-software-developer", access="paid_or_limited_preview", edition="Current catalog checked 2026; publication date not established", notes="Seven-course program, used to compare Java/OOP/data/engineering coverage. Full access and certificate pricing depend on Coursera enrollment terms.", java_specific=True),
 dict(id="course-duke", title="Java Programming and Software Engineering Fundamentals", provider="Duke / Coursera", url="https://www.coursera.org/specializations/java-programming", access="paid_or_limited_preview", edition="Current catalog checked 2026; original course is older", notes="Curriculum reference, not represented as a 2024 launch or fully free program. Public documentation replaces paid lessons in the default plan.", java_specific=True),
 dict(id="course-mit-java-legacy", title="Software Construction in Java, 6.005.1x", provider="MIT Open Learning Library", url="https://openlearninglibrary.mit.edu/courses/course-v1%3AMITx%2B6.005.1x%2B3T2016/about", access="legacy_optional", edition="Site reports created 2021; older course identifier", notes="Java-specific historical supplement outside 2024–2026. Not a required resource or a newly released course; enrollment availability was not tested.", java_specific=True),
]
for course in courses:
    course["verified_at"] = VERIFIED
    course["rights_note"] = "Course title, link and original access notes only; no course content imported."

lessons: list[dict] = []


def lesson(number: int, title: str, phase: str, prerequisites: list[int], skills: list[str],
           units: list[tuple[str, str]], practice: tuple[str, str, str], task: str,
           *, minutes: int = 240, optional: bool = False, course_refs: list[str] | None = None) -> None:
    lid = f"JB{number:02}"
    # Durations are author estimates, not publisher claims or mastery guarantees.
    lessons.append(dict(id=lid, title=title, phase=phase, prerequisite_ids=[f"JB{n:02}" for n in prerequisites],
        skill_ids=skills, optional=optional, estimated_minutes=minutes,
        duration_basis="project_estimate_including_reading_and_practice", review_status="curated_single_researcher",
        course_ids=course_refs or ["course-devjava" if phase == "Java nền tảng" else "course-spring-guides"],
        units=[dict(id=f"{lid}.U{i}",title=t,reading_ids=[r]) for i,(t,r) in enumerate(units,1)],
        practices=[dict(id=lid+".P1",title=practice[0],kind=practice[2],resource_ids=[practice[1]],
            instructions="Mở nguồn và thực hiện ví dụ/lab được liên kết trên máy cá nhân; ghi lại kết quả và những điểm chưa rõ.",
            environment="local",cost_note="Không cần đăng ký dịch vụ cloud trả phí; phần mềm cần tuân theo điều khoản của nhà cung cấp."),
            dict(id=lid+".P2",title="Vận dụng vào tình huống backend",kind="project_original",resource_ids=list(dict.fromkeys(r for _,r in units)),
            instructions=task,environment="local",cost_note="Bài vận dụng do nhóm biên soạn dựa trên các nguồn đã dẫn, không phải đề gốc của trường/nhà cung cấp.")],
        completion_note="Tự đánh dấu đã học; không phải chứng nhận thành thạo hoặc điểm đánh giá AI."))


lesson(1,"Môi trường Java, IDE và Maven","Java nền tảng",[],["java.tooling"],[("Cài JDK và chạy ứng dụng đầu tiên","java-start"),("Debug ứng dụng Java bằng VS Code","vscode"),("Build, test và đóng gói bằng Maven","maven")],("Làm Maven in 5 Minutes","maven","guided_source"),"Tạo một ứng dụng CLI ghi nhận chi tiêu, build bằng Maven và lưu hướng dẫn chạy cùng các lệnh kiểm tra phiên bản.")
lesson(2,"Cú pháp, kiểu dữ liệu và xử lý giá trị","Java nền tảng",[1],["java.language.values"],[("Biến, điều kiện, vòng lặp và method","java-basics"),("Chuỗi và giá trị số","java-strings"),("Số tiền và quy tắc làm tròn","java-money")],("Thử biểu thức với JShell","java-shell","guided_source"),"Xử lý danh sách đơn hàng có dữ liệu rỗng, số lượng âm và số tiền thập phân; liệt kê kết quả mong đợi và giải thích quyết định validation.")
lesson(3,"OOP, interface và dữ liệu bất biến","Java nền tảng",[2],["java.oop","java.immutability"],[("Đối tượng và đóng gói","java-classes"),("Interface và hợp đồng","java-interfaces"),("Record và dữ liệu bất biến","java-records"),("Kế thừa và lựa chọn composition","java-inheritance")],("Thực hiện các ví dụ record","java-records","guided_source"),"Mô hình hóa giỏ hàng, tiền và phương thức vận chuyển; giải thích phần nào dùng interface, composition hoặc record và cách tránh lộ trạng thái có thể thay đổi.")
lesson(4,"Exception, thời gian và ranh giới dữ liệu","Java nền tảng",[3],["java.exceptions","java.datetime"],[("Xử lý và phân loại exception","java-exceptions"),("Thời điểm, múi giờ và khoảng thời gian","java-time"),("Hợp đồng, đầu vào không hợp lệ và kết quả đặc biệt","mit-spec")],("Thực hiện ví dụ exception trong nguồn","java-exceptions","guided_source"),"Thiết kế nhập lịch hẹn có timezone: chỉ ra lỗi dữ liệu, lỗi hệ thống, xử lý thời điểm không hợp lệ và tài nguyên cần đóng khi thất bại.",course_refs=["course-devjava","course-mit24"])
lesson(5,"Generics, Collections và equals/hashCode","Java nền tảng",[3],["java.generics","java.collections"],[("Kiểu tổng quát và wildcard","java-generics"),("List, Set, Map và lựa chọn cấu trúc","java-collections"),("Hợp đồng equals/hashCode","java-object")],("Thử các ví dụ Collections","java-collections","guided_source"),"Thiết kế danh mục sản phẩm không trùng ID và hàng đợi xử lý đơn; so sánh cấu trúc dữ liệu và kiểm tra trường hợp hai đối tượng bằng nhau nhưng khác identity.")
lesson(6,"Lambda, Stream và phân tích chi phí","Java nền tảng",[5],["java.streams","java.algorithms.complexity"],[("Functional interface và lambda","java-lambda"),("Pipeline Stream và Collector","java-streams"),("Chi phí thao tác trên Collections","java-collections")],("Thực hiện ví dụ Stream và Collector","java-streams","guided_source"),"Tổng hợp doanh thu theo khách hàng, xử lý đơn trùng và danh sách rỗng; giải thích chi phí thời gian/bộ nhớ và tác hại của side effect.")
lesson(7,"Đặc tả, bất biến và kiểm thử nền tảng","Java nền tảng",[3],["java.testing.design","java.design.contracts"],[("MIT 2024: partition và ranh giới kiểm thử","mit-testing"),("MIT 2024: đặc tả hành vi","mit-spec"),("JUnit: tổ chức kiểm thử Java","junit"),("MIT 2024: bất biến biểu diễn","mit-invariant")],("Đọc và tự trả lời câu hỏi công khai trong MIT Testing","mit-testing","public_reading_exercises"),"Viết kế hoạch test cho hàm chuyển tiền hoặc tính phí, phân vùng đầu vào và nêu kết quả mong đợi; thực hiện test Java tại máy cá nhân nếu muốn.",course_refs=["course-mit24","course-devjava"])
lesson(8,"Concurrency, virtual thread và JVM tools","Java nền tảng",[4,7],["java.concurrency","java.jvm"],[("Executor, Future và đồng bộ","java-concurrency"),("Virtual thread và giới hạn tài nguyên","java-virtual"),("Công cụ JVM và thread dump","java-tools"),("MIT 2024: race condition và mutual exclusion","mit-locks")],("Thử các ví dụ virtual thread","java-virtual","guided_source"),"Mô phỏng nhiều yêu cầu cập nhật một bộ đếm, so sánh sai lệch trước/sau đồng bộ; phân biệt giới hạn CPU với giới hạn kết nối database.",minutes=300,course_refs=["course-devjava","course-mit24"])
lesson(9,"HTTP và hợp đồng REST API","Web và dữ liệu",[2],["backend.http","backend.api.design"],[("Luồng request/response","http"),("Method, tính an toàn và idempotency","http-methods"),("Status code và hợp đồng lỗi","http-status")],("Thử request bằng curl theo các ví dụ HTTP của MDN","http","guided_source"),"Soạn hợp đồng API quản lý đơn hàng: URL, method, status, pagination và lỗi; phân tích gửi lặp một yêu cầu tạo đơn.")
lesson(10,"SQL, truy vấn và quan hệ dữ liệu","Web và dữ liệu",[2],["backend.sql.query"],[("CS50: truy vấn và điều kiện","sql-query"),("CS50: liên kết bảng và khóa","sql-relations"),("PostgreSQL: thực hành SQL","postgres")],("Làm CS50 SQL Problem Sets 0 và phần mở rộng ở bài đọc","sql-query-pset","official_assignment"),"Thiết kế truy vấn danh sách đơn theo khách hàng, bao gồm khách chưa có đơn và dữ liệu NULL; ghi kết quả mong đợi cho dữ liệu mẫu.",course_refs=["course-harvard"])
lesson(11,"Thiết kế schema, index và tối ưu truy vấn","Web và dữ liệu",[10],["backend.sql.design","backend.sql.performance"],[("CS50: thiết kế schema và ràng buộc","sql-design"),("CS50: index và tối ưu","sql-index"),("CS50: bài tập quan hệ dữ liệu","sql-relations-pset")],("Làm CS50 SQL Problem Set 5","sql-index-pset","official_assignment"),"Thiết kế schema đơn hàng có khóa và ràng buộc; đề xuất index cho hai truy vấn khác nhau, ghi execution plan và đánh đổi chi phí ghi.",course_refs=["course-harvard"])
lesson(12,"Spring Core, Boot và cấu hình","Spring Backend",[1,3,4],["spring.core","spring.boot.configuration"],[("IoC, bean và dependency injection","ioc"),("Spring Boot: cấu hình theo môi trường","config"),("Blog Spring Boot 2024: cấu trúc và khả năng nền tảng","blog-boot24"),("Blog 2025: module và starter khi chuyển Boot 4","blog-boot4-25")],("Hoàn thành Building an Application with Spring Boot","boot-lab","guided_source"),"Tách Controller/Service/Repository cho ứng dụng quản lý sách; giải thích constructor injection và cách cấu hình local/test mà không ghi secret vào mã.",course_refs=["course-spring-guides","course-academy"])
lesson(13,"REST Controller, validation và xử lý lỗi","Spring Backend",[9,12],["spring.mvc","backend.api.validation"],[("Tạo REST endpoint","rest-lab"),("Validation đầu vào","validation-lab"),("Thiết kế tài nguyên và lỗi REST","rest-tutorial")],("Hoàn thành Building REST services with Spring","rest-tutorial","guided_source"),"Bổ sung hợp đồng lỗi cho tạo/sửa sách, phân biệt không tìm thấy, dữ liệu sai và xung đột; đề xuất kiểm tra quyền sở hữu và phân trang.")
lesson(14,"JDBC, JPA và truy vấn repository","Spring Backend",[5,10,12],["spring.persistence.jpa","backend.jdbc"],[("JDBC và tài nguyên kết nối","jdbc"),("Entity, repository và lưu trữ JPA","jpa-lab"),("Query methods và projection","jpa-query")],("Hoàn thành Accessing Data with JPA","jpa-lab","guided_source"),"Mô hình hóa khách hàng/đơn hàng, phân biệt DTO và entity; ghi những truy vấn cần chạy và cách nhận diện tải dữ liệu thừa trước khi tối ưu.",minutes=300)
lesson(15,"Transaction, isolation và tranh chấp dữ liệu","Spring Backend",[11,14],["backend.sql.transactions","spring.transactions"],[("Transaction và rollback trong Spring","tx-lab"),("Isolation và hành vi đọc/ghi","isolation"),("Khóa, deadlock và thứ tự truy cập","db-locks"),("Proxy và @Transactional","transaction")],("Hoàn thành Managing Transactions","tx-lab","guided_source"),"Phân tích hai yêu cầu mua sản phẩm cuối cùng: giữ bất biến tồn kho, rollback khi tạo đơn lỗi và xác minh bằng hai session database.",minutes=300)
lesson(16,"Spring Security, session và JWT","Spring Backend",[13],["spring.security","backend.security.authorization"],[("Filter chain và kiến trúc bảo mật","security"),("Resource server kiểm tra JWT","jwt"),("Checklist bảo mật REST","owasp")],("Hoàn thành Securing a Web Application","security-lab","guided_source"),"Thiết kế quyền xem/sửa đơn hàng: chủ sở hữu, quản trị viên, token hết hạn, ID đoán được; liệt kê ca kiểm tra quyền ở tầng tài nguyên.",minutes=300)
lesson(17,"Kiểm thử web, database và tích hợp","Spring Backend",[7,13,14],["spring.testing.integration"],[("Spring Boot test support","boot-test"),("MockMvc và kiểm thử web layer","testing-lab"),("Testcontainers: database tạm cho test","testcontainers")],("Hoàn thành Testing the Web Layer","testing-lab","guided_source"),"Xây ma trận test cho API đơn hàng: thành công, dữ liệu sai, truy cập chéo chủ sở hữu và rollback; nêu chỗ nào dùng mock, chỗ nào cần database thật.",minutes=300)
lesson(18,"Gọi dịch vụ ngoài và phục hồi lỗi","Vận hành và mở rộng",[13,17],["backend.integration.resilience"],[("RestClient và WebClient","rest-client"),("Circuit breaker và giới hạn lỗi lan truyền","breaker-lab"),("Blog Boot 3.4: HTTP client và cấu hình","blog-boot34")],("Hoàn thành Spring Cloud Circuit Breaker Guide","breaker-lab","guided_source"),"Mô tả gọi dịch vụ vận chuyển bị timeout: giới hạn thời gian, retry có điều kiện, idempotency và cách giữ kết quả chưa rõ; không gọi API trả phí.")
lesson(19,"Cache, Redis và tính nhất quán","Vận hành và mở rộng",[14,15],["backend.caching"],[("Spring cache abstraction","cache"),("Ví dụ cache chính thức của Spring","cache-lab"),("Redis data types","redis")],("Hoàn thành ví dụ gs-caching trong repo chính thức","cache-lab","guided_source"),"Đề xuất cache danh mục sách: key, TTL, invalidation sau cập nhật và xử lý dữ liệu cũ; phân biệt cache cục bộ với cache chia sẻ.")
lesson(20,"Messaging, scheduler và batch","Vận hành và mở rộng",[15,18],["backend.messaging","backend.batch"],[("Publisher/consumer với RabbitMQ","mq-lab"),("Lập lịch tác vụ","schedule-lab"),("Batch import CSV vào database","batch-lab")],("Hoàn thành Messaging with RabbitMQ","mq-lab","guided_source"),"Thiết kế gửi thông báo sau tạo đơn: message trùng, consumer lỗi, retry và dead-letter; giải thích cách tránh ghi nhận cùng sự kiện hai lần.",minutes=360)
lesson(21,"Docker, build và CI cho Java","Vận hành và mở rộng",[17],["backend.delivery.containers","backend.delivery.ci"],[("Container: tài liệu Docker 2026","docker"),("Đóng gói Spring Boot bằng Docker","docker-lab"),("Build/test Java bằng Maven trong CI","ci")],("Hoàn thành Spring Boot with Docker trên máy local","docker-lab","guided_source"),"Chuẩn bị hướng dẫn build/test và restart ứng dụng cùng database có volume; phân biệt image, container, secret và dữ liệu cần giữ. CI cloud là tùy chọn, không bắt buộc.")
lesson(22,"Quan sát hệ thống và kiểm tra hiệu năng","Vận hành và mở rộng",[18,21],["backend.observability","java.jvm.performance"],[("Actuator và health endpoint","actuator-lab"),("Logging, metrics và traces","observability"),("Java OpenTelemetry example","otel"),("Blog 2026: Optimizations in Spring MVC","blog-mvc26")],("Hoàn thành Actuator service guide","actuator-lab","guided_source"),"Theo dõi một API chậm: ghi request ID, latency, số truy vấn và lỗi; dùng JFR hoặc công cụ local, không kết luận tối ưu chỉ từ một lần đo.",minutes=300)
lesson(23,"Capstone Java Backend và ôn phỏng vấn","Vận hành và mở rộng",[15,16,17,21],["java.backend.capstone","java.design.contracts"],[("Ứng dụng tham chiếu Spring Petclinic","petclinic"),("MIT 2024: abstract data types và ranh giới module","mit-adt"),("CS50: yêu cầu dự án dữ liệu","sql-final")],("Chạy Spring Petclinic local theo README","petclinic","guided_source"),"Xây hoặc mô tả dịch vụ đặt lịch riêng: API, schema, transaction, quyền truy cập, test và deployment. Trả lời bằng lời các đánh đổi; dự án cá nhân không được chấm tự động trong app.",minutes=600,course_refs=["course-spring-guides","course-mit24","course-harvard"])
lesson(24,"Tùy chọn: cloud, microservices và reactive","Nâng cao tùy chọn",[20,22,23],["backend.cloud","backend.distributed","spring.reactive"],[("Microsoft Learn: Java trên Azure Container Apps","azure"),("Service discovery: ví dụ hai dịch vụ","discovery-lab"),("Spring WebFlux và mô hình reactive","reactive")],("Thực hiện service discovery local, không cần cloud","discovery-lab","guided_source"),"So sánh modular monolith với tách dịch vụ cho bài capstone; nêu chi phí mạng, dữ liệu và vận hành. Chỉ đọc phần Azure; nếu tự triển khai cloud phải kiểm tra chi phí trước.",minutes=360,optional=True,course_refs=["course-microsoft","course-spring-guides"])

catalog = dict(schema_version="java-roadmap/1.0",version="2026.11.27-v1",title="Lộ trình Java Backend dựa trên nguồn mở và bài đọc chính thức",
    researched_at=VERIFIED, date_policy="Prioritize explicit 2024–2026 editions/blogs and maintained pages inspected in 2026. Unknown publication dates remain null; access date is not publication date.",
    scope_note="Link catalog for self-study. External local exercises are allowed by the user's 2026-11-27 request; the interview app does not accept/run/grade code or award provider certificates.",
    review_note="Curated by one research pass; not independently reviewed assessment content. Never imported into the approved interview question bank.",
    compatibility_note="Pick one supported JDK/Spring Boot BOM for a lab and follow that version's documentation. Rolling references and 2024 blogs can describe different versions; do not mix dependency versions mechanically.",
    resources=resources,courses=courses,lessons=lessons,
    tracks={"foundation":[f"JB{i:02}" for i in range(1,12)],"backend":[f"JB{i:02}" for i in range(1,24)],"advanced":[f"JB{i:02}" for i in range(1,25)]},
    profile_bridges=[dict(source_skill_id="skill.backend.data_consistency",target_lesson_ids=["JB15"],note="Transferable database gap only; does not prove Java/Spring mastery."),
                     dict(source_skill_id="skill.algorithms.correctness_and_complexity",target_lesson_ids=["JB06"],note="Transferable complexity reasoning only; no inferred knowledge of Java syntax.")])

if __name__ == "__main__":
    target=ROOT / "data/learning/java_backend_v1.json"
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"{len(resources)} resources, {len(courses)} course references, {len(lessons)} lessons, {sum(len(l['units']) for l in lessons)} units, {sum(len(l['practices']) for l in lessons)} practices -> {target}")
