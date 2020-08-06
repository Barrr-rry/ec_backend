# 會在這邊寫 是因為api module 如果一堆文檔資訊太長 所以把他方開寫在這邊 但此專案沒有太多api 資訊
doc_desc = """
## 介接協定
- API 介接方式採用 HTTP 協定，以 GET 或 POST 方式傳遞參數，文字編碼為 UTF-8 。 

## API 路徑說明 
- [ ApiRootPath ] = [ DomainName ] + [ RootPath ]= investment-sheet.conquers.co /investment_sheet/api/v1 
    - [ DomainName ] = investment-sheet.conquers.co（ 網域 ） 
    - [ RootPath ] = / investment_sheet /api/v1（ 專案名稱/api/版本號 ） 

- Example：Login API -> [ ApiRootPath ]/login = http://investment-sheet.conquers.co /investment_sheet/api/v1/login 

## 請求方式 

- 指定 RESTful 的 HTTP Request Method 包含但不限於下列四個方式： 
    - GET ： 從伺服器取出資源（一項或多項） 
    - POST ： 在伺服器新建一個資源 
    - PUT ： 在伺服器更新資源 
    - DELETE ： 從伺服器刪除資源 

## 伺服器端參數設定 
- 限制 
    - upload_max_filesize = 10M 
    - post_max_size = 10M   




## Status Code

<table class="parameters table table-bordered table-striped">
    <thead>
    <tr>
        <th>ERROR CODE</th>
        <th>描述</th>
        <th>備註</th>
    </tr>
    </thead>
    <tbody>
    <tr>
        <td>200</td>
        <td>Success</td>
        <td>操作成功</td>
    </tr>
    <tr>
        <td>201</td>
        <td>Success</td>
        <td>成功創立資料</td>
    </tr>
    <tr>
        <td>204 (軟刪除 response 200) </td>
        <td>No Content</td>
        <td>刪除資料成功</td>
    </tr>
    <tr>
        <td>400</td>
        <td>Bad Request</td>
        <td>操作失敗(驗證或參數格式等錯誤，註冊失敗等都會出現在這邊)</td>
    </tr>
    <tr>
        <td>401</td>
        <td>Unauthorized</td>
        <td>驗證沒有通過</td>
    </tr>
    <tr>
        <td>403</td>
        <td>Forbidden</td>
        <td>禁止訪問，權限禁止</td>
    </tr>
    <tr>
        <td>404</td>
        <td>Not Found</td>
        <td>沒有發現該資源</td>
    </tr>
    <tr>
        <td>405</td>
        <td>Method Not Allowed</td>
        <td>請求錯誤 (GET, POST) 等錯誤</td>
    </tr>
    <tr>
        <td>500</td>
        <td>Internal Server Error</td>
        <td>Server 出問題</td>
    </tr>
    </tbody>
</table>

"""

file = """
        create:
        ```json
        {
            "id": 1,
            "filename": "截圖_2019-12-11_下午2.06.48.png",
            "file": "http://0.0.0.0:2000/media/%E6%88%AA%E5%9C%96_2019-12-11_%E4%B8%8B%E5%8D%882.06.48.png",
            "created": "2019-12-17T00:14:17.639991Z"
        }
        ```
        """

permission = """
    list:
    ### Request
    ```json
        {

        }
    ```
    ### Respone
    ```json

        [
          {
            "id": 1,
            "name": "高級管理員",
            "description": "超級管理員什麼都可以做",
            "role_manage": 3,
            "member_manage": 3,
            "order_manage": 3,
            "banner_manage": 3,
            "catalog_manage": 3,
            "product_manage": 3,
            "coupon_manage": 3
          },
          {
            "id": 2,
            "name": "一般管理員",
            "description": "主管 可以部分修改編輯",
            "role_manage": 2,
            "member_manage": 2,
            "order_manage": 2,
            "banner_manage": 2,
            "catalog_manage": 2,
            "product_manage": 2,
            "coupon_manage": 2
          },
          {
            "id": 3,
            "name": "基礎檢視身份",
            "description": "出貨小妹 只能看",
            "role_manage": 1,
            "member_manage": 1,
            "order_manage": 1,
            "banner_manage": 1,
            "catalog_manage": 1,
            "product_manage": 1,
            "coupon_manage": 1
          }
        ]



    ```


    create:
    ### Request
    ```json
        {
          "name": "高級管理員",
          "description": "超級管理員什麼都可以做",
          "role_manage": 3,
          "member_manage": 3,
          "order_manage": 3,
          "banner_manage": 3,
          "catalog_manage": 3,
          "product_manage": 3,
          "coupon_manage": 3
        }


    ```

    ### Response
    ```json
        {
          "id": 1,
          "name": "高級管理員",
          "description": "超級管理員什麼都可以做",
          "role_manage": 3,
          "member_manage": 3,
          "order_manage": 3,
          "banner_manage": 3,
          "catalog_manage": 3,
          "product_manage": 3,
          "coupon_manage": 3
        }
    ```

    read:
    ### Request
    ```json
    {

    }
    ```
    ### Respone
    ```json
        {
          "id": 1,
          "name": "高級管理員",
          "description": "超級管理員什麼都可以做",
          "role_manage": 3,
          "member_manage": 3,
          "order_manage": 3,
          "banner_manage": 3,
          "catalog_manage": 3,
          "product_manage": 3,
          "coupon_manage": 3
        }


    ```


    update:
    ### Request
    ```json
        {
          "name": "高級管理員",
          "description": "超級管理員什麼都可以做",
          "role_manage": 3,
          "member_manage": 3,
          "order_manage": 3,
          "banner_manage": 3,
          "catalog_manage": 3,
          "product_manage": 3,
          "coupon_manage": 3
        }


    ```
    ### Response
    ```json

        {
          "id": 1,
          "name": "高級管理員",
          "description": "超級管理員什麼都可以做",
          "role_manage": 3,
          "member_manage": 3,
          "order_manage": 3,
          "banner_manage": 3,
          "catalog_manage": 3,
          "product_manage": 3,
          "coupon_manage": 3
        }

    ```

    delete:
    ### Request
    ```json
        {
          "delete_status": true
        }

    ```
    ### Response
    ```json

    ```



    """

manager = """
     list:
     ### Request
     ```json
         {

         }
     ```
     ### Respone
     ```json

        [
          {
            "id": 1,
            "cn_name": "肉球",
            "en_name": "Meatball",
            "email": "max@conquers.co",
            "permission": 2,
            "permission_name": "一般管理員",
            "permission_description": "主管 可以部分修改編輯",
            "remarks": null,
            "status": true
          },
          {
            "id": 2,
            "cn_name": "肉球",
            "en_name": "Meatball",
            "email": "max0@conquers.co",
            "permission": 2,
            "permission_name": "一般管理員",
            "permission_description": "主管 可以部分修改編輯",
            "remarks": null,
            "status": true
          },
          {
            "id": 3,
            "cn_name": "肉球",
            "en_name": "Meatball",
            "email": "max1@conquers.co",
            "permission": 2,
            "permission_name": "一般管理員",
            "permission_description": "主管 可以部分修改編輯",
            "remarks": null,
            "status": true
          }
        ]



     ```


     create:

     ### Request
     ```json
        {
            "id": 1,
            "cn_name": "肉球",
            "en_name": "Meatball",
            "email": "max@conquers.co",
            "password": "1111",
            "permission": 2,
            "permission_name": "一般管理員",
            "permission_description": "主管 可以部分修改編輯",
            "remarks": null,
            "status": true
        }


     ```

     ### Response
     ```json
        {
            "id": 3,
            "cn_name": "肉球",
            "en_name": "Meatball",
            "email": "max1@conquers.co",
            "permission": 2,
            "permission_name": "一般管理員",
            "permission_description": "主管 可以部分修改編輯",
            "remarks": null,
            "status": true
        }
     ```

     read:
     ### Request
     ```json
         {

         }
     ```
     ### Response
     ```json
        {
            "id": 3,
            "cn_name": "肉球",
            "en_name": "Meatball",
            "email": "max1@conquers.co",
            "permission": 2,
            "permission_name": "一般管理員",
            "permission_description": "主管 可以部分修改編輯",
            "remarks": null,
            "status": true
        }
     ```


     update:

     ### Request
     ```json
        {
            "id": 3,
            "cn_name": "肉球",
            "en_name": "Meatball",
            "email": "max1@conquers.co",
            "password": "1111",
            "permission": 2,
            "permission_name": "一般管理員",
            "permission_description": "主管 可以部分修改編輯",
            "remarks": null,
            "status": true
        }


     ```
     ### Response
     ```json
        {
            "id": 3,
            "cn_name": "肉球",
            "en_name": "Meatball",
            "email": "max1@conquers.co",
            "permission": 2,
            "permission_name": "一般管理員",
            "permission_description": "主管 可以部分修改編輯",
            "remarks": null,
            "status": true
        }

     ```

     delete:
     ### Request
     ```json
        {
          "delete_status": true
        }

     ```
     ### Response
     ```json

     ```



     """

# member =
#
# occupationclassification =
