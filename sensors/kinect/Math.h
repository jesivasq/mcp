/* This Source Code Form is subject to the terms of the GNU General Public
 * License, version 3. If a copy of the GPL was not distributed with this file,
 * You can obtain one at https://www.gnu.org/licenses/gpl.txt. */

#ifndef Math_h_
#define Math_h_

#include <iostream>
#include <iomanip>
#include <sstream>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <utility>
#include <vector>

#ifdef DEBUG
#define ASSERT(c) if (!(c)) abort();
#else
#define ASSERT(c) ;
#endif

typedef double Number;

/*
 * An iterator for even subdivision of space.
 */
template <typename T>
class LinSpace
{
    T mStart;
    T mScale;
    T mCurrent;

    size_t mCount;
    size_t mPos;

  public:
    LinSpace(T start, T end, size_t count)
      : mStart(start), mScale((end - start) / (count - 1)), mCurrent(start), mCount(count), mPos(0) {}
    void begin() { mCurrent = mStart; mPos = 0; }
    bool done() { return mPos >= mCount; }
    void next() {
        mPos += 1;
        mCurrent = mStart + mPos * mScale;
    }
    T v() const { return mCurrent; }
    size_t i() const { return mPos; }
    size_t count() const { return mCount; }
};
typedef LinSpace<Number> LinSpaceT;

template <typename T>
class Vec3
{
    T v[3];

  public:
    Vec3() {}
    Vec3(T x, T y, T z) {
        set(x, y, z);
    }

    T get(int i) const {
        ASSERT(i >= 0 && i < 3);
        return v[i];
    }

    void set(int i, T t) {
        ASSERT(i >= 0 && i < 3);
        v[i] = t;
    }

    void set(T x, T y, T z) {
        v[0] = x;
        v[1] = y;
        v[2] = z;
    }

    Vec3 operator-() const {
        return Vec3(-v[0], -v[1], -v[2]);
    }

    Vec3 operator-(const Vec3 &other) const {
        Vec3 out(v[0] - other.v[0],
                 v[1] - other.v[1],
                 v[2] - other.v[2]);
        return out;
    }

    Vec3 operator+(const Vec3 &other) const {
        Vec3 out(v[0] + other.v[0],
                 v[1] + other.v[1],
                 v[2] + other.v[2]);
        return out;
    }

    Vec3 operator/(const T &scale) const {
        Vec3 out(v[0] / scale,
                 v[1] / scale,
                 v[2] / scale);
        return out;
    }

    Vec3 operator*(const T &scale) const {
        Vec3 out(v[0] * scale,
                 v[1] * scale,
                 v[2] * scale);
        return out;
    }

    double length() const {
        return sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
    }
};
typedef Vec3<Number> Vec3T;

std::ostream& operator<<(std::ostream &out, const Vec3T &v)
{
    out << "(" << v.get(0) << ", " << v.get(1) << ", " << v.get(2) << ")";
    return out;
}

template <typename T>
class Matrix44
{
    T v[4][4];

  public:
    Matrix44() {}

    Matrix44(const Matrix44 &other) {
        for (int i = 0; i < 4; ++i)
            for (int j = 0; j < 4; ++j)
                v[i][j] = other.v[i][j];
    }

    void set(int i, int j, T t) {
        ASSERT(i >= 0 && i < 4);
        ASSERT(j >= 0 && j < 4);
        v[i][j] = t;
    }

    T get(int i, int j) const {
        ASSERT(i >= 0 && i < 4);
        ASSERT(j >= 0 && j < 4);
        return v[i][j];
    }

    Matrix44 operator*(const Matrix44 &other)
    {
        Matrix44 out;
        for (int i = 0; i < 4; ++i) {
            for (int j = 0; j < 4; ++j) {
                T sum = 0;
                for (int k = 0; k < 4; ++k)
                    sum += v[i][k] * other.v[k][j];
                out.v[i][j] = sum;
            }
        }
        return out;
    }

    Vec3<T> operator*(const Vec3<T> &vec) {
        Vec3<T> out;
        for (int i = 0; i < 4; ++i) {
            T sum = 0;
            for (int j = 0; j < 3; ++j) {
                sum += v[i][j] * vec.get(j);
            }
            sum += v[i][3];
            out.set(i, sum);
        }
        return out;
    }

    static Matrix44 identity() {
        Matrix44 M = Matrix44();
        for (size_t i = 0; i < 4; ++i)
            for (size_t j = 0; j < 4; ++j)
                M.v[i][j] = 0;
        for (size_t i = 0; i < 4; ++i)
            M.v[i][i] = 1;
        return M;
    }

    static Matrix44 flipYZ() {
        Matrix44 F = identity();
        F.set(1, 1, 0);
        F.set(2, 2, 0);
        F.set(1, 2, 1);
        F.set(2, 1, 1);
        return F;
    }

    static Matrix44 scale(T s) {
        Matrix44 S = identity();
        for (size_t i = 0; i < 3; ++i)
            S.set(i, i, s);
        return S;
    }

    static Matrix44 translate(T x, T y, T z) {
        Matrix44 M = identity();
        M.set(0, 3, x);
        M.set(1, 3, y);
        M.set(2, 3, z);
        return M;
    }

    static Matrix44 translate(Vec3<T> vec) {
        return translate(vec.get(0), vec.get(1), vec.get(2));
    }

    static Matrix44 rotateXd(T axDeg) {
        T ax = DegreesToRadians(axDeg);
        T c = cos(ax);
        T s = sin(ax);
        Matrix44 R = identity();
        R.set(1, 1, c);
        R.set(1, 2, -s);
        R.set(2, 1, s);
        R.set(2, 2, c);
        return R;
    }

    static Matrix44 rotateYd(T ayDeg) {
        T ay = DegreesToRadians(ayDeg);
        T c = cos(ay);
        T s = sin(ay);
        Matrix44 R = identity();
        R.set(0, 0, c);
        R.set(0, 2, s);
        R.set(2, 0, -s);
        R.set(2, 2, c);
        return R;
    }

    static Matrix44 rotateZd(T azDeg) {
        T az = DegreesToRadians(azDeg);
        T c = cos(az);
        T s = sin(az);
        Matrix44 R = identity();
        R.set(0, 0, c);
        R.set(0, 1, -s);
        R.set(1, 0, s);
        R.set(1, 1, c);
        return R;
    }

    std::string serialize() {
        std::ostringstream strs;
        strs << std::setprecision(16);
        for (size_t i = 0; i < 4; ++i)
            for (size_t j = 0; j < 4; ++j)
                strs << v[i][j] << " ";
        return strs.str();
    }
};
typedef Matrix44<Number> Matrix44T;

template <typename T>
T DegreesToRadians(T a) { return a * M_PI / 180.0; }

template <typename T>
class Transform
{
    Vec3<T> mAng;
    Vec3<T> mPos;

  public:
    Transform() : mAng(), mPos() {}
    Transform(T aRotX, T aRotY, T aRotZ, T aX, T aY, T aZ)
      : mAng(aRotX, aRotY, aRotZ), mPos(aX, aY, aZ) {}

    Vec3<T> ang() const { return mAng; }
    Vec3<T> pos() const { return mPos; }

    void setAng(const Vec3T &v) { mAng = v; }
    void setPos(const Vec3T &v) { mPos = v; }

    Matrix44<T> matrix() const {
        return Matrix44T::rotateXd(mAng.get(0)) *
               Matrix44T::rotateYd(mAng.get(1)) *
               Matrix44T::rotateZd(mAng.get(2)) *
               Matrix44T::translate(mPos.get(0), mPos.get(1), mPos.get(2));
    }
};
typedef Transform<Number> TransformT;

std::ostream& operator<<(std::ostream &out, const TransformT &t)
{
    out << "aX:" << t.ang().get(0) << ", aY:" << t.ang().get(1) << ", aZ:" << t.ang().get(2)
        << " @ " << t.pos();
    return out;
}

#endif // Math_h_
