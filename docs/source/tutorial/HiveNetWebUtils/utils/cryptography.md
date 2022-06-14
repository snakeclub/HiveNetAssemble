# utils.cryptography模块说明

该模块提供加解密处理的通用工具, 直接使用 HCrypto 类的相关静态函数即可。



## 主要的加解密类型

### 随机数产生函数

- generate_salt ：随机生成盐字符串
- generate_nonce ：生成nonce随机字符串



### Hash散列算法

- md5：Md5加密算法
- sha1：SHA1加密算法
- sha256：SHA256加密算法
- sha512：SHA512加密算法



### 不可逆加密算法

- hmac_sha256：HMAC-SHA256加密算法



### RSA 加密

- rsa_generate_key_pair：生成RSA密钥对
- rsa_get_key：RSA获取密钥对象(公钥或私钥)
- rsa_encrypt：RSA加密数据
- rsa_decrypt：RSA解密数据
