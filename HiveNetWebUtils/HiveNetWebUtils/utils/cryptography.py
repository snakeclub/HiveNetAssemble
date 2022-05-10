#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
# Copyright 2019 黎慧剑
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
通用的加解密处理公共模块

@module cryptography
@file cryptography.py
"""

import os
import sys
import hashlib
import hmac
import base64
if sys.platform != 'win32':
    from Crypto import Random
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_v1_5
else:
    from Cryptodome import Random
    from Cryptodome.PublicKey import RSA
    from Cryptodome.Cipher import PKCS1_v1_5  # 注: JS加密的内容 PKCS1_OAEP 没有办法解密
from HiveNetCore.utils.string_tool import StringTool
# 根据当前文件路径将包路径纳入, 在非安装的情况下可以引用到
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))


__MOUDLE__ = 'cryptography'  # 模块名
__DESCRIPT__ = u'通用的加解密处理公共模块'  # 模块描述
__VERSION__ = '0.1.0'  # 版本
__AUTHOR__ = u'黎慧剑'  # 作者
__PUBLISH__ = '2020.12.08'  # 发布日期


class HCrypto(object):
    """
    通用加解密公共模块
    """

    #############################
    # 随机数产生函数
    #############################
    @classmethod
    def generate_salt(cls, str_len=8,
                      chars="AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz"):
        """
        随机生成盐字符串

        @param {int} str_len=8 - 盐长度
        @param {string} chars="AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz" - 生成盐包含的字符集合

        @returns {str} - 生成的盐字符串
        """
        return StringTool.get_random_str(
            random_length=str_len,
            chars=chars
        )

    @classmethod
    def generate_nonce(cls, length: int = 8,
                       chars="AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789") -> str:
        """
        生成nonce随机字符串

        @param {int} length=8 - 要生成的字符串长度
        @param {string} chars="AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789" - 随机抽取的字符串内容

        @returns {str} - 返回随机字符串
        """
        return StringTool.get_random_str(random_length=length, chars=chars)

    #############################
    # Hash散列算法
    #############################
    @classmethod
    def md5(cls, value, encoding='utf-8', **kwargs) -> str:
        """
        Md5加密算法

        @param {str|bytes} value - 要加密的字符串或bytes数组
        @param {str} encoding='utf-8' - 对value字符串的转换编码

        @returns {str} - 返回加密后的字符串
        """
        _value = value
        if type(value) == str:
            _value = value.encode(encoding=encoding)
        return hashlib.md5(_value).hexdigest().upper()

    @classmethod
    def sha1(cls, value: str, encoding='utf-8', **kwargs) -> str:
        """
        SHA1加密算法

        @param {str|bytes} value - 要加密的字符串或bytes数组
        @param {str} encoding='utf-8' - 对value字符串的转换编码

        @returns {str} - 返回加密后的字符串
        """
        _value = value
        if type(value) == str:
            _value = value.encode(encoding=encoding)
        return hashlib.sha1(_value).hexdigest().upper()

    @classmethod
    def sha256(cls, value: str, encoding='utf-8', **kwargs) -> str:
        """
        SHA256加密算法

        @param {str|bytes} value - 要加密的字符串或bytes数组
        @param {str} encoding='utf-8' - 对value字符串的转换编码

        @returns {str} - 返回加密后的字符串
        """
        _value = value
        if type(value) == str:
            _value = value.encode(encoding=encoding)
        return hashlib.sha256(_value).hexdigest().upper()

    @classmethod
    def sha512(cls, value: str, encoding='utf-8', **kwargs) -> str:
        """
        SHA512加密算法

        @param {str|bytes} value - 要加密的字符串或bytes数组
        @param {str} encoding='utf-8' - 对value字符串的转换编码

        @returns {str} - 返回加密后的字符串
        """
        _value = value
        if type(value) == str:
            _value = value.encode(encoding=encoding)
        return hashlib.sha512(_value).hexdigest().upper()

    #############################
    # 不可逆加密算法
    #############################
    @classmethod
    def hmac_sha256(cls, value: str, key: str, encoding='utf-8') -> str:
        """
        HMAC-SHA256加密算法

        @param {str} value - 要加密的字符串内容
        @param {str} key - 加密密钥
        @param {str} encoding='utf-8' - 对value字符串的转换编码

        @returns {str} - 返回加密后的字符串
        """
        _hash_obj = hmac.new(
            key.encode(), value.encode(encoding=encoding), digestmod=hashlib.sha256
        )
        return _hash_obj.hexdigest().upper()

    #############################
    # RSA 加密
    #############################
    @classmethod
    def rsa_generate_key_pair(cls, bits: int = 1024, e: int = 65537, format: str = 'PEM',
                              pkcs: int = 1, passphrase: str = None) -> tuple:
        """
        生成RSA密钥对

        @param {int} bits=enum[*1024,2048,3072] - 密钥长度
        @param {int} e=65537 - 公钥指数, 最小为65537, 不建议修改
        @param {str} format=enum[*'PEM','DER','OpenSSH'] - 输出的密钥格式
            PEM - 文本编码格式, 满足标准 `RFC1421`/`RFC1423`
            DER - 二进制格式
            OpenSSH - 文本编码格式, 满足 OpenSSH 标准
        @param {int} pkcs=enum[*1,8] - 私钥的结构标准
            1 - 私钥编码为简单的 PKCS#1 结构(RSAPrivateKey)
            2 - 私钥编码为 PKCS#8 结构(PrivateKeyInfo)
        @param {str} passphrase=None - 证书开启密码, 用于保护证书的输出内容

        @returns {(bytes, bytes)} - 返回 (私钥字节数组, 公钥字节数组)
        """
        _random_generator = Random.new().read
        _rsa = RSA.generate(bits, _random_generator, e=e)

        # 生成私钥
        _private_key = _rsa.exportKey(format=format, pkcs=pkcs, passphrase=passphrase)

        # 生成公钥
        _public_key = _rsa.publickey().exportKey(format=format, pkcs=pkcs)

        return (_private_key, _public_key)

    @classmethod
    def rsa_get_key(cls, extern_key, passphrase=None):
        """
        RSA获取密钥对象(公钥或私钥)

        @param {str|bytes} extern_key - 输入的密钥内容, 可以为字符串或bytes对象
        @param {str} passphrase=None - 密钥的开启密码

        @returns {Cryptodome.PublicKey.RSA.RsaKey} - 返回可以用于加解密的密钥对象
        """
        return RSA.import_key(extern_key, passphrase=passphrase)

    @classmethod
    def rsa_encrypt(cls, rsa_key, data, encoding: str = 'utf-8', output_str: bool = True):
        """
        RSA加密数据
        注意: RSA支持加密数据长度跟密钥长度有关,因此不建议使用RSA加密大数据

        @param {Cryptodome.PublicKey.RSA.RsaKey} rsa_key - 通过 rsa_get_key 获取到的 RsaKey 对象
        @param {str|bytes} data - 要加密的数据, 支持字符串或字节数据两种类型
        @param {str} encoding='utf-8' - 对字符串的转换编码
        @param {bool} output_str=True - 输出结果是否转换为字符串格式

        @returns {str|bytes} - 如果output_str为True, 则通过 base64.b64encode 转换为可打印字符输出, 否则返回二进制字节数组
        """
        _cipher_rsa = PKCS1_v1_5.new(rsa_key)

        # 进行数据转换
        _data = data
        if type(data) == str:
            _data = bytes(data, encoding=encoding)

        # 进行加密处理
        _encrypt_data = _cipher_rsa.encrypt(_data)

        # 将加密结果转换为 base64 编码字符串
        if output_str:
            return base64.b64encode(_encrypt_data).decode(encoding='ascii')
        else:
            return _encrypt_data

    @classmethod
    def ras_decrypt(cls, rsa_key, encrypt_data, output_str: bool = True, encoding: str = 'utf-8'):
        """
        解密数据

        @param {Cryptodome.PublicKey.RSA.RsaKey} rsa_key - 通过 rsa_get_key 获取到的 RsaKey 对象
        @param {str|bytes} encrypt_data - 要解密的数据, 支持 base64 字符串或字节数据两种类型
        @param {bool} output_str=True - 输出结果是否转换为真实字符串 (加密数据为字符串)
        @param {str} encoding='utf-8' - 数据结果转换为字符串的编码

        @returns {bytes|str} - 解密后的结果, 如果 output_str 为 True 则为字符串, 否则为二进制字节数组
        """
        _cipher_rsa = PKCS1_v1_5.new(rsa_key)

        # 进行数据处理
        _encrypt_data = encrypt_data
        if type(encrypt_data) == str:
            _encrypt_data = base64.b64decode(bytes(_encrypt_data, encoding='ascii'))

        # 解密
        _bytes_data = _cipher_rsa.decrypt(_encrypt_data, None)

        # 看是否转换为字符串
        if output_str:
            return _bytes_data.decode(encoding=encoding)
        else:
            return _bytes_data


if __name__ == '__main__':
    # 当程序自己独立运行时执行的操作
    # 打印版本信息
    print(('模块名: %s  -  %s\n'
           '作者: %s\n'
           '发布日期: %s\n'
           '版本: %s' % (__MOUDLE__, __DESCRIPT__, __AUTHOR__, __PUBLISH__, __VERSION__)))
