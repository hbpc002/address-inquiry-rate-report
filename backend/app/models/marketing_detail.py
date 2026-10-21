from sqlalchemy import Column, Integer, String, Date, DateTime
from sqlalchemy.sql import func
from app.models.database import Base


class MarketingDetail(Base):
    """营销明细（线上直办新口径明细资产）"""

    __tablename__ = "marketing_details"

    id = Column(Integer, primary_key=True, index=True)
    kf_id = Column(String(50), index=True, comment="客服工号")
    org_name = Column(String(500), index=True, comment="员工组织（RESERVE6/预留字段6）")
    organization = Column(String(500), index=True, comment="组织机构（ORG_NAME/组织机构）")
    tenant = Column(String(100), index=True, comment="建单租户（办理工单来源）")
    work_order_id = Column(String(100), index=True, comment="工单流水号")
    data_type = Column(String(20), index=True, comment="数据类型，如 xszb 线上直办、fwgd 办理工单")
    pos_sequence = Column(String(100), comment="人员岗位性质")
    develop_depart_name = Column(String(255), comment="发展渠道")
    develop_depart_id = Column(String(50))
    develop_staff_name = Column(String(100))
    develop_staff_id = Column(String(50))
    tb_region_name = Column(String(50))
    channel = Column(String(50), comment="受理渠道")
    area_name = Column(String(50), comment="地市")
    net_type = Column(String(20), comment="网别")
    trade_id = Column(String(50), index=True, comment="CBSS订单号")
    finish_date = Column(Date, nullable=False, index=True, comment="CBSS订单竣工日期")
    service_type = Column(String(50), index=True, comment="重点业务分类")
    package_type = Column(String(255), comment="叠加包分类")
    valid_type = Column(String(50), comment="叠加包有效期")
    product_id = Column(String(50), index=True)
    product_name = Column(String(200))
    lh_qh = Column(String(20), index=True, comment="来话/去话")
    is_zero = Column(String(10), comment="0元/非0元")
    import_batch = Column(String(50), index=True)
    created_at = Column(DateTime, server_default=func.now())
