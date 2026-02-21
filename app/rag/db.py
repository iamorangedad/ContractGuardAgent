import os
import sqlite3
from typing import Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(DATA_DIR, "contracts.db")

def get_db_path() -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    return DB_PATH

def init_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS templates_fts USING fts5(
            title, category, content, content=templates, content_rowid=id
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS playbook (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            action TEXT NOT NULL,
            keywords TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS playbook_fts USING fts5(
            rule_name, category, description, risk_level, keywords,
            content=playbook, content_rowid=id
        )
    """)
    
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS templates_ai AFTER INSERT ON templates BEGIN
            INSERT INTO templates_fts(rowid, title, category, content)
            VALUES (new.id, new.title, new.category, new.content);
        END
    """)
    
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS templates_ad AFTER DELETE ON templates BEGIN
            INSERT INTO templates_fts(templates_fts, rowid, title, category, content)
            VALUES ('delete', old.id, old.title, old.category, old.content);
        END
    """)
    
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS playbook_ai AFTER INSERT ON playbook BEGIN
            INSERT INTO playbook_fts(rowid, rule_name, category, description, risk_level, keywords)
            VALUES (new.id, new.rule_name, new.category, new.description, new.risk_level, new.keywords);
        END
    """)
    
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM templates")
    if cursor.fetchone()[0] == 0:
        seed_template_data(cursor)
    
    cursor.execute("SELECT COUNT(*) FROM playbook")
    if cursor.fetchone()[0] == 0:
        seed_playbook_data(cursor)
    
    conn.commit()
    conn.close()

def seed_template_data(cursor):
    templates = [
        ("标准采购合同模板", "采购", """采购合同

甲方（供应商）：________________
乙方（采购方）：________________

一、合同金额
本合同总金额为人民币______元（大写：______元整）。

二、付款方式
1. 合同签订后5个工作日内，乙方支付合同总金额的30%作为预付款；
2. 货物交付验收合格后5个工作日内，乙方支付合同总金额的60%；
3. 质保期满后5个工作日内，乙方支付剩余10%尾款。

三、交货时间
甲方应在合同签订后______日内完成交货。

四、质量保证
1. 产品质量符合国家标准；
2. 质保期为货物验收合格之日起12个月；
3. 甲方对产品质量负责，因质量问题造成的损失由甲方承担。

五、违约责任
1. 甲方逾期交货的，每逾期一天按合同总金额的0.5%支付违约金；
2. 乙方逾期付款的，每逾期一天按应付金额的0.5%支付违约金；
3. 双方任何一方违约导致合同解除的，违约方按合同总金额的20%支付违约金。

六、争议解决
本合同在履行过程中发生的争议，由双方协商解决；协商不成的，提交乙方所在地人民法院诉讼解决。

七、合同生效
本合同一式两份，甲乙双方各执一份，自双方签字盖章之日起生效。

甲方（盖章）：________________    乙方（盖章）：________________
签字：________________          签字：________________
日期：________________          日期：________________"""),

        ("标准服务合同模板", "服务", """服务合同

甲方（委托方）：________________
乙方（受托方）：________________

一、服务内容
乙方为甲方提供以下服务：
1. ________________；
2. ________________；
3. ________________。

二、服务费用
1. 本合同服务费用为人民币______元（大写：______元整）；
2. 付款方式：______。

三、服务期限
本合同服务期限为______年/月，自______年______月______日起至______年______月______日止。

四、双方权利义务
1. 甲方应按约定支付服务费用；
2. 乙方应按约定提供服务，确保服务质量；
3. 乙方应对工作中知悉的甲方商业秘密予以保密。

五、违约责任
1. 乙方未按约定提供服务的，甲方有权扣减相应服务费用；
2. 任何一方擅自解除合同的，应向对方支付合同总额20%的违约金。

六、争议解决
因本合同发生的争议，双方应协商解决；协商不成的，提交甲方所在地人民法院管辖。

七、其他
本合同未尽事宜，由双方另行协商解决。

甲方（盖章）：________________    乙方（盖章）：________________
签字：________________          签字：________________
日期：________________          日期：________________"""),

        ("标准租赁合同模板", "租赁", """租赁合同

甲方（出租方）：________________
乙方（承租方）：________________

一、租赁物信息
甲方将以下财产出租给乙方使用：
位置/名称：________________
面积/数量：________________

二、租金及支付方式
1. 租金为人民币______元/月（大写：______元整）；
2. 支付方式：乙方应于每______月______日前支付租金；
3. 押金：乙方应向甲方支付押金______元。

三、租赁期限
租赁期限为______年，自______年______月______日起至______年______月______日止。

四、维修保养
1. 甲方负责租赁物的基本维修；
2. 乙方应合理使用租赁物，造成损坏的应承担维修费用。

五、违约责任
1. 乙方逾期支付租金的，每逾期一天按月租金的0.5%支付滞纳金；
2. 未经甲方同意，乙方擅自转租的，甲方有权解除合同。

六、争议解决
本合同履行中发生争议的，双方应协商解决；协商不成的，提交租赁物所在地人民法院管辖。

七、合同生效
本合同自双方签字盖章之日起生效。

甲方（盖章）：________________    乙方（盖章）：________________
签字：________________          签字：________________
日期：________________          日期：________________"""),

        ("标准劳动合同模板", "劳动", """劳动合同

甲方（用人单位）：________________
乙方（劳动者）：________________

一、合同期限
本合同为固定期限劳动合同，合同期限为______年，自______年______月______日起至______年______月______日止。

二、工作内容和工作地点
1. 乙方在______部门担任______岗位工作；
2. 工作地点为：______。

三、工作时间和休息休假
1. 乙方执行标准工时制；
2. 乙方依法享有法定节假日、年休假等假期。

四、劳动报酬
1. 乙方月工资为人民币______元；
2. 甲方应于每月______日前以货币形式支付乙方工资；
3. 加班工资按国家规定计算。

五、社会保险
甲方应依法为乙方缴纳养老、医疗、失业、工伤、生育保险。

六、违约责任
1. 甲方未按约定支付劳动报酬的，应按应付金额的100%支付赔偿金；
2. 双方任何一方违反本合同约定的，应承担相应法律责任。

七、争议解决
因履行本合同发生的争议，双方应协商解决；协商不成的，可以向劳动争议仲裁委员会申请仲裁。

八、其他
本合同未尽事宜，按国家有关规定执行。

甲方（盖章）：________________    乙方（签字）：________________
日期：________________          日期：________________"""),

        ("标准保密协议模板", "保密", """保密协议

甲方：________________
乙方：________________

鉴于乙方在甲方任职或参与甲方项目，可能接触到甲方的商业秘密，为保护甲方合法权益，双方经协商一致签订本协议。

一、保密信息范围
1. 技术信息：技术方案、设计图纸、研究成果等；
2. 经营信息：客户名单、营销计划、财务数据等；
3. 其他甲方标明为保密的信息。

二、保密义务
1. 乙方应对保密信息严格保密，未经甲方书面同意不得向任何第三方披露；
2. 乙方应仅在履行工作职责所必需的范围内使用保密信息；
3. 乙方离职时应返还所有保密信息载体。

三、保密期限
本协议约定的保密义务期限为劳动合同存续期间及劳动关系解除后______年。

四、违约责任
1. 乙方违反本协议约定的，应向甲方支付违约金______元；
2. 乙方泄露甲方商业秘密造成甲方损失的，应承担赔偿责任。

五、争议解决
因本协议发生的争议，双方应协商解决；协商不成的，提交甲方所在地人民法院管辖。

六、其他
本协议自双方签字盖章之日起生效。

甲方（盖章）：________________    乙方（签字）：________________
日期：________________          日期：________________"""),
    ]
    
    cursor.executemany(
        "INSERT INTO templates (title, category, content) VALUES (?, ?, ?)",
        templates
    )

def seed_playbook_data(cursor):
    playbook_rules = [
        ("付款比例", "采购", "预付款不超过合同金额的30%，验收款不超过60%，尾款不低于10%", "绿色", "建议调整付款比例", "预付款,30%,验收款,60%"),
        ("付款比例", "采购", "预付款超过40%或验收款超过70%", "红色", "预付款比例过高，不符合公司财务规定", "预付款,40%,验收款,70%"),
        ("违约金上限", "通用", "违约金不超过合同金额的20%", "绿色", "符合标准", "违约金,20%"),
        ("违约金上限", "通用", "违约金超过合同金额的30%", "红色", "违约金过高，可能存在法律风险", "违约金,30%"),
        ("管辖法院", "通用", "优先选择原告所在地或被告所在地法院", "绿色", "符合标准", "管辖法院,原告,被告"),
        ("管辖法院", "通用", "约定由外地的仲裁机构或法院管辖", "黄色", "异地管辖会增加维权成本，建议修改为本地", "仲裁,外地"),
        ("质保期", "采购", "质保期不少于12个月", "绿色", "符合标准", "质保,12月"),
        ("质保期", "采购", "质保期少于6个月", "黄色", "质保期较短，建议延长至12个月", "质保,6月"),
        ("知识产权", "服务", "服务成果知识产权归甲方所有", "绿色", "符合标准", "知识产权,甲方"),
        ("知识产权", "服务", "服务成果知识产权归乙方所有或共有", "红色", "知识产权归属不符合公司利益", "知识产权,乙方,共有"),
        ("竞业限制", "劳动", "竞业限制期限不超过2年", "绿色", "符合标准", "竞业,2年"),
        ("竞业限制", "劳动", "竞业限制期限超过3年或无补偿", "红色", "竞业限制期限过长或违反劳动法规定", "竞业,3年,无补偿"),
        ("押金", "租赁", "押金不超过2个月租金", "绿色", "符合标准", "押金,2月"),
        ("押金", "租赁", "押金超过3个月租金", "黄色", "押金过高，建议降低", "押金,3月"),
        ("保密期限", "保密", "保密期限不超过劳动关系解除后2年", "绿色", "符合标准", "保密,2年"),
        ("保密期限", "保密", "保密期限为永久或过长", "黄色", "永久保密可能无法执行，建议限定合理期限", "永久,保密"),
    ]
    
    cursor.executemany(
        "INSERT INTO playbook (rule_name, category, description, risk_level, action, keywords) VALUES (?, ?, ?, ?, ?, ?)",
        playbook_rules
    )

def escape_fts_query(query: str) -> str:
    import re
    query = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', query)
    words = query.split()
    if not words:
        return '"*"'
    return ' OR '.join(f'"{w}"' for w in words[:10])

def search_templates(query: str, top_k: int = 3) -> list:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    fts_query = escape_fts_query(query)
    
    cursor.execute("""
        SELECT t.* FROM templates t
        JOIN templates_fts fts ON t.id = fts.rowid
        WHERE templates_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """, (fts_query, top_k))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

def search_playbook(query: str, category: str = None, top_k: int = 5) -> list:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    fts_query = escape_fts_query(query)
    
    if category:
        cursor.execute("""
            SELECT p.* FROM playbook p
            JOIN playbook_fts fts ON p.id = fts.rowid
            WHERE playbook_fts MATCH ? AND p.category = ?
            ORDER BY rank
            LIMIT ?
        """, (fts_query, category, top_k))
    else:
        cursor.execute("""
            SELECT p.* FROM playbook p
            JOIN playbook_fts fts ON p.id = fts.rowid
            WHERE playbook_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (fts_query, top_k))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

def get_all_playbook_rules(category: str = None) -> list:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if category:
        cursor.execute("SELECT * FROM playbook WHERE category = ?", (category,))
    else:
        cursor.execute("SELECT * FROM playbook")
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
