import hashlib
import hmac
import urllib.parse

class Vnpay:
    requestData = {}
    responseData = {}

    def get_payment_url(self, vnpay_payment_url, secret_key):
        # Loại bỏ các tham số rỗng và params hash theo yêu cầu VNPAY
        filtered = {k: v for k, v in self.requestData.items() if v is not None and str(v) != '' and k not in ['vnp_SecureHash', 'vnp_SecureHashType']}
        inputData = sorted(filtered.items())

        query_parts = []
        for key, val in inputData:
            # Sử dụng quote thay vì quote_plus để tránh lỗi encoding
            encoded_val = urllib.parse.quote(str(val), safe='')
            query_parts.append(f"{key}={encoded_val}")

        queryString = "&".join(query_parts)

        # Tạo chữ ký từ toàn bộ queryString sau khi sắp xếp và encode
        hashValue = self.__hmacsha512(secret_key, queryString)
        payment_url = vnpay_payment_url + "?" + queryString + '&vnp_SecureHash=' + hashValue
        
        # Debug log
        print(f"VNPAY Create URL Debug:")
        print(f"Query String: {queryString}")
        print(f"Hash Value: {hashValue}")
        print(f"Secret Key: {secret_key[:8]}...")
        
        return payment_url

    def validate_response(self, secret_key):
        vnp_SecureHash = self.responseData.get('vnp_SecureHash')
        if not vnp_SecureHash:
            return False
        # Remove hash params
        if 'vnp_SecureHash' in self.responseData.keys():
            self.responseData.pop('vnp_SecureHash')

        if 'vnp_SecureHashType' in self.responseData.keys():
            self.responseData.pop('vnp_SecureHashType')

        # Bỏ hash params trước khi ký lại
        filtered = {k: v for k, v in self.responseData.items() if k not in ['vnp_SecureHash', 'vnp_SecureHashType']}
        inputData = sorted(filtered.items())
        hasData = ''
        seq = 0
        for key, val in inputData:
            if str(key).startswith('vnp_'):
                if seq == 1:
                    hasData = hasData + "&" + str(key) + '=' + urllib.parse.quote(str(val), safe='')
                else:
                    seq = 1
                    hasData = str(key) + '=' + urllib.parse.quote(str(val), safe='')
        hashValue = self.__hmacsha512(secret_key, hasData)

        # Debug log
        print(f"VNPAY Validate Response Debug:")
        print(f"Has Data: {hasData}")
        print(f"Received Hash: {vnp_SecureHash}")
        print(f"Calculated Hash: {hashValue}")
        print(f"Secret Key: {secret_key[:8]}...")

        # So sánh không phân biệt hoa thường để tránh lệch định dạng hex
        return str(vnp_SecureHash).upper() == str(hashValue).upper()

    @staticmethod
    def __hmacsha512(key, data):
        byteKey = key.encode('utf-8')
        byteData = data.encode('utf-8')
        return hmac.new(byteKey, byteData, hashlib.sha512).hexdigest()
