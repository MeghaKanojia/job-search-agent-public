-- DEMO REPO NOTE: this is fictional sample data, published as part of a
-- sanitized portfolio/demo replica of a private personal project. No real
-- employer or project is represented here -- only the candidate's name
-- (in backend/app/api/routes/documents.py) is real.
--
-- Run once against your Neon database, after migration_002_profile_sections.sql:
--   psql $DATABASE_URL -f backend/db/seed_profile.sql
-- Everything here is editable afterwards from the Profile page.

INSERT INTO education (institution, degree, field_of_study, location, start_date, end_date, grade, description, sort_order) VALUES
('Riverdale University', 'Master of Science in Computing', 'Data Analytics', 'Dublin, Ireland', '2025-09-01', '2026-08-26', 'First Class Honours (1:1)',
 'Key focus areas: Machine Learning, Cloud Technologies, Time Series Analysis, Data Analytics and Mining, Foundations of Statistical Analysis, AI, Information Seeking, Data Management and Visualization.', 0),
('Northfield Institute of Engineering and Technology', 'Bachelor of Technology', 'Computer Science & Engineering', 'Jaipur, India', '2018-08-01', '2022-05-31', 'CGPA: 8.24/10',
 NULL, 1);

INSERT INTO work_experience (company, role_title, location, start_date, end_date, is_current, description, sort_order) VALUES
('Nimbus Health Analytics', 'Data Team Lead', 'Gurugram, India', '2024-06-01', '2025-08-31', FALSE,
$$Optimized an enterprise analytics stack (Adobe Analytics, Power BI, an internal metrics platform) serving 500+ users, cutting support ticket latency by 30% and maintaining a 99.99% system uptime.
Accelerated onboarding velocity for 4+ junior data engineers by 40% through the development of automated onboarding modules and data compliance training frameworks.$$, 0),
('Nimbus Health Analytics', 'Data Scientist / Software Engineer (Data & Analytics)', 'Gurugram, India', '2022-06-01', '2024-05-31', FALSE,
$$Automated financial and operational reporting workflows for 500+ users, reducing manual analytics overhead by 30% through the design and maintenance of unified Power BI and Adobe Analytics KPI dashboards.
Spearheaded strategic product data mapping initiatives across 100+ global teams, accelerating stakeholder decision-making by translating complex technical datasets into clear business insights and data stories.
Engineered custom Python and Linux automation recovery scripts to trigger immediate alerts and auto-restarts, driving pipeline efficiency and maintaining a 99% service uptime.
Negotiated a 15% reduction in cloud infrastructure costs by leading a full-scale migration to a cloud content platform while ensuring 99.9% application parity.
Enforced data security compliance and access control standards across the enterprise ecosystem by administering Role-Based Access Control (RBAC) protocols for downstream data analysts and scientists.
Leveraged AI coding assist tools (GitHub Copilot) to improve code quality and delivery speed across data pipeline and ML model development workflows, validating AI-generated outputs through peer review and automated testing while maintaining secure coding standards.$$, 1),
('DataForge Labs', 'Machine Learning Engineer Intern', 'Remote, India', '2020-09-01', '2020-12-31', FALSE,
$$Built an automated Python (Pandas/NumPy) data validation pipeline that identified and resolved 15% missing value gaps across 200K+ records, establishing a 99% data integrity threshold for downstream financial modeling.
Enhanced model interpretability for non-technical business partners by designing 5+ interactive diagnostic visualizations leveraging Matplotlib and Seaborn.
Boosted predictive model accuracy by 12% across 10+ distinct algorithms (including Random Forest and XGBoost) utilizing Grid Search Cross-Validation hyperparameter tuning.$$, 2);

INSERT INTO projects (title, description, tech_stack, project_url, sort_order) VALUES
('Grammy vs Spotify: Critical Acclaim vs Commercial Success',
 'End-to-end PySpark ETL pipeline investigating the divergence between Grammy-winning songs and Spotify popularity. Built three distinct cohorts, resolved cross-dataset entity mismatches via regex and manual mapping, and produced interactive visualisations comparing audio features across 2000-2023.',
 'PySpark, Apache Spark, Pandas, Parquet, Seaborn, Google Colab, ipywidgets',
 'https://github.com/demo-sample-profile/grammy-spotify-analysis', 0),
('Detecting AI-Generated Product Images on an Online Marketplace',
 'Three-phase ML study classifying AI-generated vs authentic product images. Progressed from frozen CNN plus classical ML (F1: 0.81) through EfficientNetV2-S fine-tuning (F1: 0.91) to a ConvNeXt-Base model with an FFT frequency branch, reaching a validation F1 of 0.9356. Rigorous ablations on augmentation, TTA, and threshold tuning.',
 'PyTorch, TensorFlow, timm, ConvNeXt, EfficientNetV2, Focal Loss, SWA, scikit-learn, OpenCV',
 'https://github.com/demo-sample-profile/ai-image-detection-demo', 1),
('Retail E-Commerce Sales ETL Pipeline',
 'Production-style ETL pipeline merging 231K+ grocery transactions with economic feature data (CPI, unemployment, fuel prices). Cleaned and filtered to 106K analysis-ready records, revealing November-December holiday demand peaks averaging $39K weekly vs $32K in October.',
 'Python, Pandas, SQL, Parquet, PyArrow',
 'https://github.com/demo-sample-profile/retail-etl-pipeline', 2),
('Forecasting Atmospheric Radioactivity - Regional Monitoring Network',
 'Comparative study of SARIMA, ETS, and TBATS models on 9 years of monthly atmospheric radiation data from a regional monitoring network, achieving a top test RMSE of 22.26. Rigorous train-test validation revealed SARIMA generalises best despite ETS winning in-sample, a key lesson in overfitting. Contribution: TBATS trigonometric seasonal modelling and feature engineering.',
 'R, forecast, SARIMA, TBATS, ETS, tseries, ggplot2, R Markdown',
 'https://github.com/demo-sample-profile/forecasting-radioactivity-demo', 3);

-- issue_date left NULL throughout, same as the private original -- fill in via
-- the Profile page if you want them shown.
INSERT INTO certifications (name, issuing_organization, description, sort_order) VALUES
('Leadership Development Program', 'Northwind Consulting', 'Advanced Business Leadership, Structured Problem Solving, and Cross-Functional Communication.', 0),
('Azure Fundamentals (AZ-900)', 'Microsoft', NULL, 1),
('Google Data Analytics Professional Certificate', 'Google', NULL, 2),
('Excellence in Technical Delivery Award', 'Nimbus Health Analytics', 'Recognized for technical excellence and predictive modeling.', 3),
('Cross-Functional Collaboration Award', 'Nimbus Health Analytics', 'Earned for cross-functional agile stakeholder management.', 4),
('Data Quality Excellence Award', 'Nimbus Health Analytics', 'Attained a 100% MBO score via data security enhancements on an internal analytics platform.', 5);

INSERT INTO skill_profile_items (skill_name, category, sort_order) VALUES
('Python', 'Data Science & ML', 0),
('Pandas', 'Data Science & ML', 1),
('NumPy', 'Data Science & ML', 2),
('Scikit-learn', 'Data Science & ML', 3),
('PyTorch', 'Data Science & ML', 4),
('TensorFlow', 'Data Science & ML', 5),
('Random Forest', 'Data Science & ML', 6),
('XGBoost', 'Data Science & ML', 7),
('Time-Series Forecasting (SARIMA, ETS, TBATS)', 'Data Science & ML', 8),
('NLP', 'Data Science & ML', 9),
('Statistical Analysis', 'Data Science & ML', 10),
('C', 'Data Science & ML', 11),
('C++', 'Data Science & ML', 12),
('SQL', 'Data Engineering & Cloud', 13),
('MySQL', 'Data Engineering & Cloud', 14),
('Snowflake', 'Data Engineering & Cloud', 15),
('Apache Spark', 'Data Engineering & Cloud', 16),
('PySpark', 'Data Engineering & Cloud', 17),
('Parquet', 'Data Engineering & Cloud', 18),
('Microsoft Azure (AZ-900)', 'Data Engineering & Cloud', 19),
('Azure Functions', 'Data Engineering & Cloud', 20),
('Google BigQuery', 'Data Engineering & Cloud', 21),
('Looker', 'Data Engineering & Cloud', 22),
('ETL/ELT Pipelines', 'Data Engineering & Cloud', 23),
('OLTP/OLAP Databases', 'Data Engineering & Cloud', 24),
('Databricks', 'Data Engineering & Cloud', 25),
('AWS', 'Data Engineering & Cloud', 26),
('CI/CD Workflows', 'Data Engineering & Cloud', 27),
('Power BI', 'Analytics & Business Intelligence', 28),
('DAX', 'Analytics & Business Intelligence', 29),
('Tableau', 'Analytics & Business Intelligence', 30),
('Adobe Analytics', 'Analytics & Business Intelligence', 31),
('KPI Tracking', 'Analytics & Business Intelligence', 32),
('Data Storytelling', 'Analytics & Business Intelligence', 33),
('Linux Scripting', 'Automation & Practices', 34),
('Workflow Automation', 'Automation & Practices', 35),
('Git', 'Automation & Practices', 36),
('Agile Development', 'Automation & Practices', 37),
('Data Governance', 'Automation & Practices', 38),
('Stakeholder Communication', 'Automation & Practices', 39),
('Java', 'Data Structures & Algorithms', 40),
('OOP', 'Data Structures & Algorithms', 41),
('Operating Systems', 'Data Structures & Algorithms', 42),
('Computer Organization and Architecture', 'Data Structures & Algorithms', 43);
-- No unique constraint on skill_name (same as the rest of this table), so
-- re-running this file will duplicate every row above -- run it once only.
