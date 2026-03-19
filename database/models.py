from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, BigInteger, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.engine import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    tg_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)   # set after contact shared
    language = Column(String, default="kk")
    balance = Column(Float, default=0.0)
    total_spent = Column(Float, default=0.0)
    is_banned = Column(Boolean, default=False)
    is_vip = Column(Boolean, default=False)
    # Referral system
    referred_by = Column(BigInteger, ForeignKey('users.tg_id'), nullable=True)
    referral_count = Column(Integer, default=0)
    referral_bonus = Column(Float, default=0.0)
    # Daily bonus
    last_daily_bonus_claimed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    purchases = relationship("Purchase", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    keys = relationship("Key", back_populates="user")

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    vip_price = Column(Float, nullable=True)  # Dynamic VIP pricing
    description = Column(String, nullable=True)
    
    purchases = relationship("Purchase", back_populates="product")
    keys = relationship("Key", back_populates="product")

class Key(Base):
    __tablename__ = 'keys'
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    key_value = Column(String, unique=True, nullable=False)
    is_used = Column(Boolean, default=False)
    used_by = Column(BigInteger, ForeignKey('users.tg_id'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    product = relationship("Product", back_populates="keys")
    user = relationship("User", back_populates="keys", foreign_keys=[used_by])
    purchase = relationship("Purchase", back_populates="key", uselist=False)

class Purchase(Base):
    __tablename__ = 'purchases'
    id = Column(Integer, primary_key=True, index=True)
    user_tg_id = Column(BigInteger, ForeignKey('users.tg_id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    key_id = Column(Integer, ForeignKey('keys.id'), nullable=False)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="purchases")
    product = relationship("Product", back_populates="purchases")
    key = relationship("Key", back_populates="purchase", foreign_keys=[key_id])

class Payment(Base):
    __tablename__ = 'payments'
    id = Column(Integer, primary_key=True, index=True)
    user_tg_id = Column(BigInteger, ForeignKey('users.tg_id'), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String, default="pending") # pending, approved, rejected
    receipt_file_id = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="payments")

class VipCode(Base):
    __tablename__ = 'vip_codes'
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)
    is_used = Column(Boolean, default=False)
    used_by = Column(BigInteger, ForeignKey('users.tg_id'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PromoCode(Base):
    __tablename__ = 'promo_codes'
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)
    discount_percent = Column(Float, nullable=True)  # % жеңілдік
    bonus_amount = Column(Float, nullable=True)  # немесе тікелей сома қосу
    is_single_use = Column(Boolean, default=True)  # бір реттік немесе көп реттік
    is_active = Column(Boolean, default=True)
    used_count = Column(Integer, default=0)
    max_uses = Column(Integer, nullable=True)  # null = шектеусіз
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    uses = relationship("PromoCodeUse", back_populates="promo_code")

class PromoCodeUse(Base):
    __tablename__ = 'promo_code_uses'
    id = Column(Integer, primary_key=True, index=True)
    promo_code_id = Column(Integer, ForeignKey('promo_codes.id'), nullable=False)
    user_tg_id = Column(BigInteger, ForeignKey('users.tg_id'), nullable=False)
    used_at = Column(DateTime(timezone=True), server_default=func.now())
    
    promo_code = relationship("PromoCode", back_populates="uses")

class SupportTicket(Base):
    __tablename__ = 'support_tickets'
    id = Column(Integer, primary_key=True, index=True)
    user_tg_id = Column(BigInteger, ForeignKey('users.tg_id'), nullable=False)
    message = Column(String, nullable=False)
    status = Column(String, default="open")  # open, in_progress, closed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    user = relationship("User")
    replies = relationship("SupportReply", back_populates="ticket")

class SupportReply(Base):
    __tablename__ = 'support_replies'
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey('support_tickets.id'), nullable=False)
    sender_tg_id = Column(BigInteger, nullable=False)  # әкімші немесе пайдаланушы
    message = Column(String, nullable=False)
    is_from_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    ticket = relationship("SupportTicket", back_populates="replies")
